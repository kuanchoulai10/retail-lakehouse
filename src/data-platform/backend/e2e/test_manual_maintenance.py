"""A manual maintenance request runs all four operations on a table, one after the other, and each does its work.

The table gets 20 single-row appends and a delete, so it has many small files and many snapshots.
A dry-run policy keeps the platform from maintaining it on its own; once its last write is older
than the policy's snapshot age, a manual request runs the four operations of one plan. Afterwards
the table has fewer files and snapshots, the storage holds no more objects than the runs account
for, and the records, the catalog API and Temporal agree on what happened.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pyarrow as pa
import pytest
from pyarrow import fs
from pyiceberg.partitioning import PartitionField, PartitionSpec
from pyiceberg.schema import Schema
from pyiceberg.transforms import BucketTransform, DayTransform
from pyiceberg.types import DoubleType, LongType, NestedField, StringType, TimestamptzType

from e2e.support import (
    ManagedTable,
    OwnedNames,
    assert_attempts_timed,
    assert_prefixed_ids,
    assert_runs_succeeded,
    reconciliation_running,
    wait_until,
)

if TYPE_CHECKING:
    from pyiceberg.catalog import Catalog
    from temporalio.client import Client

    from e2e.support import CleanupStack, E2eSettings, PlatformApi, TemporalSession

pytestmark = pytest.mark.full

PLAN = ("rewrite_data_files", "rewrite_manifests", "expire_snapshots", "remove_orphan_files")
EXPIRE_AGE_SECONDS = 60
RUN_TIMEOUT_SECONDS = 3600
RECONCILE_TIMEOUT_SECONDS = 300
ACTIVE = ("pending", "queued", "running")
SCHEMA = Schema(
    NestedField(1, "id", LongType(), required=False),
    NestedField(2, "customer", StringType(), required=False),
    NestedField(3, "amount", DoubleType(), required=False),
    NestedField(4, "order_ts", TimestamptzType(), required=False),
)
SPEC = PartitionSpec(
    PartitionField(source_id=4, field_id=1000, transform=DayTransform(), name="order_ts_day"),
    PartitionField(source_id=1, field_id=1001, transform=BucketTransform(4), name="id_bucket"),
)
ROWS = pa.schema(
    [("id", pa.int64()), ("customer", pa.string()), ("amount", pa.float64()), ("order_ts", pa.timestamp("us", "UTC"))]
)


def _manual_runs_only(policy: dict) -> dict:
    policy["dry_run"] = True
    policy["rewrite_data_files"]["options"]["min_input_files"] = 1
    policy["expire_snapshots"]["target"] = {"min_snapshots_to_keep": 1, "max_snapshot_age_seconds": EXPIRE_AGE_SECONDS}
    policy["remove_orphan_files"]["target"]["older_than_seconds"] = 86400
    return policy


def _at(text: str) -> datetime:
    return datetime.fromisoformat(text)


def _quiet(platform: PlatformApi, table_uuid: str) -> bool:
    active = [(run["operation"], run["status"]) for run in platform.runs(table_uuid) if run["status"] in ACTIVE]
    if active:
        raise AssertionError(f"runs in flight: {active}")
    return True


def _settled_manual_plan(platform: PlatformApi, table_uuid: str, before: set[str]) -> list[dict]:
    runs = [run for run in platform.runs(table_uuid) if run["run_id"] not in before]
    manual = [run for run in runs if run["trigger"] == "manual"]
    if len(manual) < len(PLAN) or any(run["status"] in ACTIVE for run in runs):
        raise AssertionError(f"manual plan not ended: {[(r['operation'], r['status']) for r in runs]}")
    return runs


def _objects_under(s3: fs.S3FileSystem, prefix: str) -> int:
    selector = fs.FileSelector(prefix, recursive=True, allow_not_found=True)
    return sum(1 for info in s3.get_file_info(selector) if info.type == fs.FileType.File)


def test_a_manual_request_runs_the_four_operations_of_one_plan(
    platform: PlatformApi,
    iceberg: Catalog,
    s3: fs.S3FileSystem,
    temporal: TemporalSession[Client],
    settings: E2eSettings,
    suffix: str,
    cleanup: CleanupStack,
):
    """The manual runs are one plan run in order, compact the whole table, and leave it smaller."""
    orders = ManagedTable.create(
        platform=platform,
        iceberg=iceberg,
        s3=s3,
        temporal=temporal,
        cleanup=cleanup,
        catalog=settings.catalog,
        namespace=OwnedNames.namespace(suffix, "orders"),
        name="tm_e2e_orders",
        schema=SCHEMA,
        partition_spec=SPEC,
        policy=(
            OwnedNames.maintenance_policy(suffix, "orders"),
            "e2e: manual runs only, lowered target values",
            _manual_runs_only,
        ),
        discovery_policy=OwnedNames.discovery_policy(suffix, "orders"),
    )
    table = orders.load(iceberg)
    for n in range(1, 21):
        day = datetime(2026, 10, n % 2 + 1, 10, tzinfo=UTC)
        row = {"id": n, "customer": f"customer-{n}", "amount": n + 0.5, "order_ts": day}
        table.append(pa.Table.from_pylist([row], schema=ROWS))
    table.delete("id == 3")
    last_write = time.monotonic()
    uuid = orders.wait_until_managed(platform)
    wait_until(lambda: _quiet(platform, uuid), timeout=RUN_TIMEOUT_SECONDS, interval=15, what=f"{uuid} quiet")
    time.sleep(max(0.0, last_write + EXPIRE_AGE_SECONDS + 5 - time.monotonic()))

    table = orders.load(iceberg)
    data = table.location().removeprefix("s3://").rstrip("/") + "/data"
    files_before = table.inspect.files().num_rows
    snapshots_before = len(table.metadata.snapshots)
    objects_before = _objects_under(s3, data)
    before = {run["run_id"] for run in platform.runs(uuid)}

    effective = platform.get(f"/v1/tables/{uuid}/effective-policies")["policies"]
    assert [(e["kind"], e["policy_name"], e["attachment_id"]) for e in effective] == [
        ("maintenance", orders.maintenance_policy, orders.maintenance_attachment_id),
        ("discovery", orders.discovery_policy["name"], orders.discovery_attachment_id),
    ]

    platform.call("POST", f"/v1/tables/{uuid}/maintenance", {"operations": list(PLAN)})
    runs = wait_until(
        lambda: _settled_manual_plan(platform, uuid, before),
        timeout=RUN_TIMEOUT_SECONDS,
        interval=15,
        what=f"the manual plan of {uuid}",
    )
    assert_runs_succeeded(runs)
    assert_attempts_timed(runs)
    manual = sorted((run for run in runs if run["trigger"] == "manual"), key=lambda run: PLAN.index(run["operation"]))
    assert [run["operation"] for run in manual] == list(PLAN)
    assert len({run["execution_ref"] for run in manual}) == 1, [run["execution_ref"] for run in manual]
    assert len({run["created_at"] for run in manual}) == 1, [run["created_at"] for run in manual]
    for previous, run in zip(manual, manual[1:], strict=False):
        assert _at(run["started_at"]) >= _at(previous["finished_at"]), (previous, run)
    [compaction] = [run for run in manual if run["operation"] == "rewrite_data_files"]
    assert platform.get(f"/v1/table-maintenance-runs/{compaction['run_id']}")["partitions"] == []

    started = sorted((run["operation"], run["run_id"]) for run in manual)
    reconciliations = platform.get(f"/v1/tables/{uuid}/reconciliations")
    assert any(
        record["wake_reasons"].get("manual_run", 0) >= 1
        and sorted((o["operation"], o["run_id"]) for o in record["operations"] if o["result"] == "started") == started
        for record in reconciliations
    ), f"no reconciliation links the manual runs {started}"

    wait_until(lambda: _quiet(platform, uuid), timeout=RUN_TIMEOUT_SECONDS, interval=15, what=f"{uuid} quiet")
    recorded = {record["reconciliation_id"] for record in platform.get(f"/v1/tables/{uuid}/reconciliations")}
    platform.call("POST", f"/v1/tables/{uuid}/reconcile")

    def reconciled_now() -> bool | None:
        records = platform.get(f"/v1/tables/{uuid}/reconciliations")
        found = any(
            r["reconciliation_id"] not in recorded and r["wake_reasons"].get("reconcile_now", 0) >= 1 for r in records
        )
        return True if found else None

    wait_until(reconciled_now, timeout=RECONCILE_TIMEOUT_SECONDS, interval=5, what=f"a reconcile-now record of {uuid}")

    table = orders.load(iceberg)
    files_after = table.inspect.files().num_rows
    snapshots_after = len(table.metadata.snapshots)
    objects_after = _objects_under(s3, data)
    assert files_after < files_before, f"files {files_before} -> {files_after}"
    assert snapshots_after < snapshots_before, f"snapshots {snapshots_before} -> {snapshots_after}"
    _assert_objects_accounted(runs, objects_before, objects_after)
    _assert_catalog_api_agrees(platform, settings, orders, uuid, files_after, snapshots_after)

    assert reconciliation_running(temporal, uuid)
    assert compaction["execution_ref"] == f"table-maintenance:table-uuid={uuid}"
    _assert_found_by_table(temporal, uuid)
    assert_prefixed_ids(
        {
            "mr": [run["run_id"] for run in manual],
            "rc": [record["reconciliation_id"] for record in reconciliations],
            "dr": [rule["id"] for rule in orders.discovery_policy["rules"]],
            "mp": [platform.get(f"/v1/maintenance-policies/{orders.maintenance_policy}")["id"]],
            "dp": [orders.discovery_policy["id"]],
            "da": [orders.discovery_attachment_id],
            "pa": [orders.maintenance_attachment_id],
        }
    )


def _assert_objects_accounted(runs: list[dict], before: int, after: int) -> None:
    """The storage holds no more objects than the compaction added and the expiry left (unless a callback was lost)."""
    if any(run["metrics"].get("completed_without_callback") for run in runs):
        return
    added = sum(r["metrics"].get("added_data_files_count", 0) for r in runs if r["operation"] == "rewrite_data_files")
    deleted = sum(
        r["metrics"].get(key, 0)
        for r in runs
        if r["operation"] == "expire_snapshots"
        for key in (
            "deleted_data_files_count",
            "deleted_position_delete_files_count",
            "deleted_equality_delete_files_count",
        )
    )
    assert deleted > 0, "expire_snapshots deleted no files"
    assert after <= before + added - deleted, {"before": before, "added": added, "deleted": deleted, "after": after}


def _assert_catalog_api_agrees(
    platform: PlatformApi, settings: E2eSettings, orders: ManagedTable, uuid: str, files: int, snapshots: int
) -> None:
    """The catalog API lists the table and its metadata counts what PyIceberg counts; commits come newest first."""
    under = f"/v1/catalogs/{settings.catalog}/namespaces/{orders.namespace}/tables"
    assert orders.name in [entry["name"] for entry in platform.get(under)]
    metadata = platform.get(f"{under}/{orders.name}")
    assert metadata["uuid"] == uuid
    [current] = [s for s in metadata["snapshots"] if s["id"] == metadata["current_snapshot_id"]]
    summary = current["summary"]
    assert int(summary.get("total-data-files", 0)) + int(summary.get("total-delete-files", 0)) == files
    assert len(metadata["snapshots"]) == snapshots
    commits = [_at(item["committed_at"]) for item in platform.get(f"/v1/tables/{uuid}/commits", limit=1000)["items"]]
    assert commits, "no commits"
    assert commits[0] == max(commits), "commits are not newest first"


def _assert_found_by_table(temporal: TemporalSession[Client], uuid: str) -> None:
    """Temporal's TableUuid search attribute finds the table's reconciliation and its maintenance workflow."""
    wanted = {f"table-reconciliation:table-uuid={uuid}", f"table-maintenance:table-uuid={uuid}"}

    async def workflow_ids(client: Client) -> set[str]:
        return {execution.id async for execution in client.list_workflows(f'TableUuid = "{uuid}"')}

    wait_until(
        lambda: True if wanted <= temporal.run(workflow_ids) else None,
        timeout=60,
        interval=5,
        what=f'TableUuid = "{uuid}" finding {sorted(wanted)}',
    )
