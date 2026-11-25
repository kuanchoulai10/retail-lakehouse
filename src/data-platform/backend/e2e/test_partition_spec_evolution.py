"""A compaction of a table whose partition spec changed rewrites the partitions of both specs, one entry each.

The table is partitioned by ``day(ts)`` and ``bucket(id, 4)``; three appends write into two days
and two buckets, so each of those four partitions holds three files. The spec then drops the
bucket field, and three more appends write into one day under the new spec. Once the writes are
quiet, a check compacts the five partitions over a target of one reducible file: the run records
spec 0 with its four partitions and spec 1 with its one. Iceberg writes the rewritten files under
the current spec, so spec 0 ends with fewer files and the table with fewer in all.
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
from pyiceberg.transforms import BucketTransform, DayTransform
from pyiceberg.types import LongType, NestedField, TimestamptzType

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
    from temporalio.client import Client

    from e2e.support import CleanupStack, E2eSettings, PlatformApi, TemporalSession

pytestmark = pytest.mark.full

RUN_TIMEOUT_SECONDS = 900
ACTIVE = ("pending", "queued", "running", "retry_waiting")
SCHEMA = Schema(
    NestedField(1, "id", LongType(), required=False),
    NestedField(2, "ts", TimestamptzType(), required=False),
)
SPEC = PartitionSpec(
    PartitionField(source_id=2, field_id=1000, transform=DayTransform(), name="ts_day"),
    PartitionField(source_id=1, field_id=1001, transform=BucketTransform(4), name="id_bucket"),
)
ROWS = pa.schema([("id", pa.int64()), ("ts", pa.timestamp("us", tz="UTC"))])
DAYS = (datetime(2026, 11, 1, 12, tzinfo=UTC), datetime(2026, 11, 2, 12, tzinfo=UTC))


def _compaction_only(policy: dict) -> dict:
    for operation in ("rewrite_manifests", "expire_snapshots", "remove_orphan_files"):
        policy.pop(operation, None)
    policy["on"] = {"schedule": {"every_seconds": 3600}}
    policy["rewrite_data_files"]["target"] = {"reducible_files": {"at_most": 1}, "per": "partition"}
    policy["rewrite_data_files"]["options"]["min_input_files"] = 2
    return policy


def _two_buckets() -> tuple[int, int]:
    """Return two ids that ``bucket(id, 4)`` puts in different buckets."""
    bucket = BucketTransform(4).transform(LongType())
    first = 1
    second = next(n for n in range(2, 100) if bucket(n) != bucket(first))
    return first, second


def _files_per_spec(table: ManagedTable, iceberg: Catalog) -> Counter[int]:
    files = table.load(iceberg).inspect.files().to_pylist()
    return Counter(row["spec_id"] for row in files if row["content"] == 0)


def _ended(platform: PlatformApi, table_uuid: str, run_id: str) -> dict:
    [run] = [run for run in platform.runs(table_uuid) if run["run_id"] == run_id]
    if run["status"] in ACTIVE:
        raise AssertionError(f"run {run_id} is {run['status']}")
    return run


def test_a_compaction_across_two_specs_records_one_entry_per_spec(
    platform: PlatformApi,
    iceberg: Catalog,
    s3: fs.S3FileSystem,
    temporal: TemporalSession[Client],
    settings: E2eSettings,
    suffix: str,
    cleanup: CleanupStack,
):
    """Spec 0 with its fields and four partitions, spec 1 with the day alone, and fewer files."""
    quiet = require_settings(platform, maintenance_compaction_quiet_seconds=60)["maintenance_compaction_quiet_seconds"]
    evolved = ManagedTable.create(
        platform=platform,
        iceberg=iceberg,
        s3=s3,
        temporal=temporal,
        cleanup=cleanup,
        catalog=settings.catalog,
        namespace=OwnedNames.namespace(suffix, "spec_evolution"),
        name="tm_e2e_spec_evolution",
        schema=SCHEMA,
        partition_spec=SPEC,
        policy=(
            OwnedNames.maintenance_policy(suffix, "spec_evolution"),
            "e2e: per-partition compaction across two specs, checked on request",
            _compaction_only,
        ),
        discovery_policy=OwnedNames.discovery_policy(suffix, "spec_evolution"),
    )
    uuid = evolved.wait_until_managed(platform)
    ids = _two_buckets()
    table = evolved.load(iceberg)
    for n in range(3):
        rows = [{"id": i, "ts": day + timedelta(minutes=n)} for day in DAYS for i in ids]
        table.append(pa.Table.from_pylist(rows, schema=ROWS))
    with table.update_spec() as update:
        update.remove_field("id_bucket")
    table = evolved.load(iceberg)
    for n in range(3):
        table.append(pa.Table.from_pylist([{"id": n, "ts": DAYS[0] + timedelta(hours=n)}], schema=ROWS))
    before = _files_per_spec(evolved, iceberg)
    assert before == {0: 12, 1: 3}, before
    newest = evolved.load(iceberg).current_snapshot()
    assert newest is not None
    last_write = datetime.fromtimestamp(newest.timestamp_ms / 1000, UTC)

    time.sleep(max(0.0, (last_write + timedelta(seconds=quiet) - datetime.now(UTC)).total_seconds() + 2))
    compaction = next(o for o in reconcile_now(platform, uuid)["operations"] if o["operation"] == "rewrite_data_files")
    assert compaction["result"] == "started", compaction
    run = wait_until(
        lambda: _ended(platform, uuid, compaction["run_id"]),
        timeout=RUN_TIMEOUT_SECONDS,
        interval=10,
        what=f"the compaction of {uuid}",
    )
    assert_runs_succeeded([run])

    specs = platform.get(f"/v1/table-maintenance-runs/{run['run_id']}")["partitions"]
    assert [spec["spec_id"] for spec in specs] == [0, 1], specs
    first, second = specs
    assert [(f["column"], f["transform"]) for f in first["fields"]] == [("ts", "day"), ("id", "bucket[4]")], first
    assert [(f["column"], f["transform"]) for f in second["fields"]] == [("ts", "day")], second
    assert len(first["partitions"]) == 4, first
    assert all(len(values) == 2 for values in first["partitions"]), first
    assert len(second["partitions"]) == 1, second
    after = _files_per_spec(evolved, iceberg)
    assert after[0] < before[0], (before, after)
    assert sum(after.values()) < sum(before.values()), (before, after)
