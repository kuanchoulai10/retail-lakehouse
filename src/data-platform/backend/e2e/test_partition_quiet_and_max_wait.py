"""A quiet partition is compacted while a written one waits, and the written one goes after the longest wait.

The table is partitioned by ``region``. ``cold`` gets four appends and ``hot`` three, then a
writer keeps appending to ``hot`` every 15 s, well inside the quiet period. The first check finds
both waiting for their writes to settle. Once ``cold`` is quiet, a check compacts it alone while
``hot`` waits. ``hot`` never goes quiet, so it is compacted only once it has been over the target
for the longest wait, with the writer still appending: no append fails on a commit conflict.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pyarrow as pa
import pytest
from pyiceberg.partitioning import PartitionField, PartitionSpec
from pyiceberg.schema import Schema
from pyiceberg.transforms import IdentityTransform
from pyiceberg.types import LongType, NestedField, StringType

from e2e.support import (
    BackgroundWriter,
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
    from temporalio.client import Client

    from e2e.support import CleanupStack, E2eSettings, PlatformApi, TemporalSession

pytestmark = pytest.mark.full

RUN_TIMEOUT_SECONDS = 900
WRITE_EVERY_SECONDS = 15
ACTIVE = ("pending", "queued", "running")
SELECTION = ("qualifying_partitions", "selected_partitions", "waiting_partitions")
SCHEMA = Schema(
    NestedField(1, "id", LongType(), required=False),
    NestedField(2, "region", StringType(), required=False),
)
SPEC = PartitionSpec(PartitionField(source_id=2, field_id=1000, transform=IdentityTransform(), name="region"))
ROWS = pa.schema([("id", pa.int64()), ("region", pa.string())])


def _compaction_only(policy: dict) -> dict:
    for operation in ("rewrite_manifests", "expire_snapshots", "remove_orphan_files"):
        policy.pop(operation, None)
    policy["on"] = {"schedule": {"every_seconds": 3600}}
    policy["rewrite_data_files"]["target"] = {"reducible_files": {"at_most": 1}, "per": "partition"}
    policy["rewrite_data_files"]["options"]["min_input_files"] = 2
    return policy


def _at(text: str) -> datetime:
    return datetime.fromisoformat(text)


def _compaction(record: dict) -> dict:
    [found] = [operation for operation in record["operations"] if operation["operation"] == "rewrite_data_files"]
    return found


def _selection(operation: dict) -> tuple[int, ...]:
    measured = {m["key"]: m["observed"] for m in operation["measurements"]}
    return tuple(measured[key] for key in SELECTION)


def _ended(platform: PlatformApi, table_uuid: str, run_id: str) -> dict:
    [run] = [run for run in platform.runs(table_uuid) if run["run_id"] == run_id]
    if run["status"] in ACTIVE:
        raise AssertionError(f"run {run_id} is {run['status']}")
    return run


def _compacted(platform: PlatformApi, run_id: str) -> list[list[str | None]]:
    specs = platform.get(f"/v1/table-maintenance-runs/{run_id}")["partitions"]
    assert [spec["spec_id"] for spec in specs] == [0], specs
    return specs[0]["partitions"]


def test_a_quiet_partition_goes_first_and_a_written_one_after_the_longest_wait(
    platform: PlatformApi,
    iceberg: Catalog,
    s3: fs.S3FileSystem,
    temporal: TemporalSession[Client],
    settings: E2eSettings,
    suffix: str,
    cleanup: CleanupStack,
):
    """Both wait, then cold alone, then hot once overdue, its run succeeding while the writer appends."""
    waits = require_settings(
        platform,
        maintenance_compaction_quiet_seconds=60,
        maintenance_compaction_max_quiet_wait_seconds=180,
        maintenance_rewrite_data_files_cooldown_seconds=60,
    )
    quiet = timedelta(seconds=waits["maintenance_compaction_quiet_seconds"])
    longest = timedelta(seconds=waits["maintenance_compaction_max_quiet_wait_seconds"])
    assert quiet > timedelta(seconds=2 * WRITE_EVERY_SECONDS), f"hot would go quiet between writes: {quiet}"
    regions = ManagedTable.create(
        platform=platform,
        iceberg=iceberg,
        s3=s3,
        temporal=temporal,
        cleanup=cleanup,
        catalog=settings.catalog,
        namespace=OwnedNames.namespace(suffix, "quiet_wait"),
        name="tm_e2e_quiet_wait",
        schema=SCHEMA,
        partition_spec=SPEC,
        policy=(
            OwnedNames.maintenance_policy(suffix, "quiet_wait"),
            "e2e: per-partition compaction under writes, checked on request",
            _compaction_only,
        ),
        discovery_policy=OwnedNames.discovery_policy(suffix, "quiet_wait"),
    )
    uuid = regions.wait_until_managed(platform)
    table = regions.load(iceberg)
    for n in range(4):
        table.append(pa.Table.from_pylist([{"id": n, "region": "cold"}], schema=ROWS))
    cold_written = datetime.now(UTC)
    for n in range(3):
        table.append(pa.Table.from_pylist([{"id": 100 + n, "region": "hot"}], schema=ROWS))

    def append_hot(index: int) -> None:
        regions.load(iceberg).append(pa.Table.from_pylist([{"id": 1000 + index, "region": "hot"}], schema=ROWS))

    writer = BackgroundWriter.start(append_hot, every_seconds=WRITE_EVERY_SECONDS)
    cleanup.push("stop the writes to hot", writer.stop)

    first = reconcile_now(platform, uuid)
    assert _compaction(first)["result"] == "waiting_for_writes", first
    assert _selection(_compaction(first)) == (2, 0, 2), _compaction(first)

    time.sleep(max(0.0, (cold_written + quiet - datetime.now(UTC)).total_seconds() + 2))
    cold = _compaction(reconcile_now(platform, uuid))
    assert cold["result"] == "started", cold
    assert _selection(cold) == (2, 1, 1), cold
    cold_run = wait_until(
        lambda: _ended(platform, uuid, cold["run_id"]),
        timeout=RUN_TIMEOUT_SECONDS,
        interval=10,
        what=f"the compaction of cold in {uuid}",
    )
    assert_runs_succeeded([cold_run])
    assert _compacted(platform, cold_run["run_id"]) == [["cold"]]

    def hot_started() -> dict:
        record = reconcile_now(platform, uuid)
        operation = _compaction(record)
        if operation["result"] != "started":
            raise AssertionError(f"compaction {operation['result']} until {operation['next_eligible_at']}")
        return record | {"compaction": operation}

    hot = wait_until(hot_started, timeout=longest.total_seconds() + 300, interval=20, what=f"hot compacted in {uuid}")
    overdue_at = _at(first["reconciled_at"]) + longest
    assert _at(hot["reconciled_at"]) >= overdue_at - timedelta(seconds=2), (hot["reconciled_at"], overdue_at)
    assert writer.running, "the writer stopped before hot was compacted"
    hot_run = wait_until(
        lambda: _ended(platform, uuid, hot["compaction"]["run_id"]),
        timeout=RUN_TIMEOUT_SECONDS,
        interval=10,
        what=f"the compaction of hot in {uuid}",
    )
    appended = writer.stop()
    assert_runs_succeeded([hot_run])
    assert [attempt["attempt"] for attempt in hot_run["attempts"]] == [1], hot_run["attempts"]
    assert hot_run["metrics"].get("failed_data_files_count", 0) == 0, hot_run["metrics"]
    assert _compacted(platform, hot_run["run_id"]) == [["hot"]]
    assert appended >= longest.total_seconds() // WRITE_EVERY_SECONDS, f"only {appended} appends committed"
