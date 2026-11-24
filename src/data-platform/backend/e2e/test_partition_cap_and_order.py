"""A compaction takes at most ten partitions, the ones with most reducible files first, and the rest next time.

The table is partitioned by ``region``; 13 appends leave ``rNN`` with ``NN + 1`` files, so the 11
partitions ``r02`` to ``r12`` are over a target of one reducible file. Right after the writes a
check waits for them to settle, until the quiet period after ``r02``'s last write, the earliest.
Once every partition is quiet, one check starts a compaction of ``r03`` to ``r12`` (the cap leaves
``r02`` out without counting it as waiting) and, the snapshots being old enough by then, an expiry
after it. The policy turns partial progress off: with it, Iceberg commits each partition on its own
from several threads, and a commit that loses the race too often is dropped while the procedure
still succeeds, which is not what this scenario checks. The next check compacts ``r02``; one
inside the compaction cooldown starts nothing (the expiry usually outlasts that cooldown, so the
check after it may start ``r02`` at once).
"""

from __future__ import annotations

import time
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pyarrow as pa
import pytest
from pyiceberg.partitioning import PartitionField, PartitionSpec
from pyiceberg.schema import Schema
from pyiceberg.transforms import IdentityTransform
from pyiceberg.types import LongType, NestedField, StringType

from e2e.support import (
    ManagedTable,
    OwnedNames,
    assert_runs_succeeded,
    reconcile_now,
    require_settings,
    wait_until,
)

if TYPE_CHECKING:
    from pyarrow import fs
    from pyiceberg.catalog import Catalog
    from pyiceberg.table.snapshots import Snapshot
    from temporalio.client import Client

    from e2e.support import CleanupStack, E2eSettings, PlatformApi, TemporalSession

pytestmark = pytest.mark.full

RUN_TIMEOUT_SECONDS = 900
EXPIRE_AGE_SECONDS = 60
REGIONS = [f"r{n:02d}" for n in range(1, 13)]
ACTIVE = ("pending", "queued", "running")
SELECTION = ("qualifying_partitions", "selected_partitions", "waiting_partitions")
SCHEMA = Schema(
    NestedField(1, "id", LongType(), required=False),
    NestedField(2, "region", StringType(), required=False),
)
SPEC = PartitionSpec(PartitionField(source_id=2, field_id=1000, transform=IdentityTransform(), name="region"))
ROWS = pa.schema([("id", pa.int64()), ("region", pa.string())])


def _compaction_and_expiry(policy: dict) -> dict:
    for operation in ("rewrite_manifests", "remove_orphan_files"):
        policy.pop(operation, None)
    policy["dry_run"] = False
    policy["on"] = {"schedule": {"every_seconds": 3600}}
    policy["rewrite_data_files"]["target"] = {"reducible_files": {"at_most": 1}, "per": "partition"}
    policy["rewrite_data_files"]["options"]["min_input_files"] = 2
    policy["rewrite_data_files"]["options"]["partial_progress_enabled"] = False
    policy["expire_snapshots"]["target"] = {"min_snapshots_to_keep": 1, "max_snapshot_age_seconds": EXPIRE_AGE_SECONDS}
    return policy


def _at(text: str) -> datetime:
    return datetime.fromisoformat(text)


def _operation(record: dict, name: str) -> dict:
    [found] = [operation for operation in record["operations"] if operation["operation"] == name]
    return found


def _measured(operation: dict) -> dict[str, int]:
    return {m["key"]: m["observed"] for m in operation["measurements"]}


def _sleep_until(instant: datetime) -> None:
    time.sleep(max(0.0, (instant - datetime.now(UTC)).total_seconds() + 2))


def _committed_at(snapshot: Snapshot) -> datetime:
    return datetime.fromtimestamp(snapshot.timestamp_ms / 1000, UTC)


def _ended(platform: PlatformApi, table_uuid: str, run_ids: list[str]) -> list[dict]:
    runs = [run for run in platform.runs(table_uuid) if run["run_id"] in run_ids]
    if len(runs) < len(run_ids) or any(run["status"] in ACTIVE for run in runs):
        raise AssertionError(f"runs not ended: {[(run['operation'], run['status']) for run in runs]}")
    return runs


def _files_per_region(orders: ManagedTable, iceberg: Catalog) -> Counter[str]:
    files = orders.load(iceberg).inspect.files().to_pylist()
    return Counter(row["partition"]["region"] for row in files if row["content"] == 0)


def test_a_compaction_takes_the_ten_partitions_with_most_files_and_the_rest_next_time(
    platform: PlatformApi,
    iceberg: Catalog,
    s3: fs.S3FileSystem,
    temporal: TemporalSession[Client],
    settings: E2eSettings,
    suffix: str,
    cleanup: CleanupStack,
):
    """Quiet first, ten partitions most files first with the expiry after them, then the eleventh after the cooldown."""
    waits = require_settings(
        platform, maintenance_compaction_quiet_seconds=60, maintenance_rewrite_data_files_cooldown_seconds=60
    )
    assert platform.platform_setting("maintenance_compaction_partitions_per_job") == 10
    regions = ManagedTable.create(
        platform=platform,
        iceberg=iceberg,
        s3=s3,
        temporal=temporal,
        cleanup=cleanup,
        catalog=settings.catalog,
        namespace=OwnedNames.namespace(suffix, "partition_cap"),
        name="tm_e2e_partition_cap",
        schema=SCHEMA,
        partition_spec=SPEC,
        policy=(
            OwnedNames.maintenance_policy(suffix, "partition_cap"),
            "e2e: per-partition compaction and expiry, checked on request",
            _compaction_and_expiry,
        ),
        discovery_policy=OwnedNames.discovery_policy(suffix, "partition_cap"),
    )
    uuid = regions.wait_until_managed(platform)
    table = regions.load(iceberg)
    for k in range(1, 14):
        rows = [{"id": k, "region": region} for n, region in enumerate(REGIONS, start=1) if n + 1 >= k]
        table.append(pa.Table.from_pylist(rows, schema=ROWS))
    appends = sorted(regions.load(iceberg).snapshots(), key=lambda snapshot: snapshot.sequence_number)
    assert len(appends) == 13, [snapshot.snapshot_id for snapshot in appends]
    quiet = timedelta(seconds=waits["maintenance_compaction_quiet_seconds"])
    assert _files_per_region(regions, iceberg) == {region: n + 1 for n, region in enumerate(REGIONS, start=1)}
    before = {run["run_id"] for run in platform.runs(uuid)}

    waiting = reconcile_now(platform, uuid)
    compaction = _operation(waiting, "rewrite_data_files")
    assert compaction["result"] == "waiting_for_writes", compaction
    assert {key: _measured(compaction)[key] for key in SELECTION} == dict(zip(SELECTION, (11, 0, 11), strict=True))
    r02_quiet = _committed_at(appends[2]) + quiet
    assert abs((_at(compaction["next_eligible_at"]) - r02_quiet).total_seconds()) <= 2, (compaction, r02_quiet)
    assert {run["run_id"] for run in platform.runs(uuid)} == before, "a run started while the writes settled"
    metrics_before = platform.get(f"/v1/tables/{uuid}/metrics/current")["metrics"]

    _sleep_until(_committed_at(appends[-1]) + quiet)
    started = reconcile_now(platform, uuid)
    compaction, expiry = _operation(started, "rewrite_data_files"), _operation(started, "expire_snapshots")
    assert (compaction["result"], expiry["result"]) == ("started", "started"), started
    assert {key: _measured(compaction)[key] for key in SELECTION} == dict(zip(SELECTION, (11, 10, 0), strict=True))
    assert compaction["run_id"] != expiry["run_id"]
    runs = wait_until(
        lambda: _ended(platform, uuid, [compaction["run_id"], expiry["run_id"]]),
        timeout=RUN_TIMEOUT_SECONDS,
        interval=10,
        what=f"the compaction and expiry of {uuid}",
    )
    assert_runs_succeeded(runs)
    by_operation = {run["operation"]: run for run in runs}
    assert {run["trigger"] for run in runs} == {"scheduled"}
    assert _at(by_operation["expire_snapshots"]["started_at"]) >= _at(by_operation["rewrite_data_files"]["finished_at"])
    [spec] = platform.get(f"/v1/table-maintenance-runs/{compaction['run_id']}")["partitions"]
    assert spec["spec_id"] == 0
    assert sorted(value for [value] in spec["partitions"]) == REGIONS[2:]
    files = _files_per_region(regions, iceberg)
    assert files == {"r01": 2, "r02": 3} | dict.fromkeys(REGIONS[2:], 1), files

    ended = _at(by_operation["rewrite_data_files"]["attempts"][-1]["finished_at"])
    cooldown = timedelta(seconds=waits["maintenance_rewrite_data_files_cooldown_seconds"])
    after = reconcile_now(platform, uuid)
    assert _operation(after, "expire_snapshots")["result"] == "cooling_down", after
    rest = _operation(after, "rewrite_data_files")
    if rest["result"] == "cooling_down":
        assert abs((_at(rest["next_eligible_at"]) - (ended + cooldown)).total_seconds()) <= 30, (rest, ended)
        _sleep_until(_at(rest["next_eligible_at"]))
        rest = _operation(reconcile_now(platform, uuid), "rewrite_data_files")
    else:
        assert _at(after["reconciled_at"]) >= ended + cooldown, "the cooldown let a compaction start inside it"
    assert rest["result"] == "started", rest
    metrics_after = platform.get(f"/v1/tables/{uuid}/metrics/current")["metrics"]
    assert metrics_after["data_files"] < metrics_before["data_files"], (metrics_before, metrics_after)
    assert metrics_after["reducible_files"] < metrics_before["reducible_files"], (metrics_before, metrics_after)
    [last] = wait_until(
        lambda: _ended(platform, uuid, [rest["run_id"]]),
        timeout=RUN_TIMEOUT_SECONDS,
        interval=10,
        what=f"the second compaction of {uuid}",
    )
    assert_runs_succeeded([last])
    specs = platform.get(f"/v1/table-maintenance-runs/{last['run_id']}")["partitions"]
    assert [(spec["spec_id"], spec["partitions"]) for spec in specs] == [(0, [["r02"]])], specs
    assert _files_per_region(regions, iceberg)["r02"] == 1
