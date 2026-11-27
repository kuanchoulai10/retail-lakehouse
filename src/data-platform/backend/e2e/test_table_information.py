"""What the platform tells about one table: its record, metrics, schema and partition versions, commits.

One dry-run table in a catalog of the module's own, managed while empty, then written once, evolved
(a rename, a widened and loosened column and a nested column in one commit), written again, given an
hourly partition spec instead of a daily one and written a third time. Marked ``full``: it waits for
discovery and for a reconciliation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pyarrow as pa
import pytest
from pyiceberg.partitioning import PartitionField, PartitionSpec
from pyiceberg.schema import Schema
from pyiceberg.transforms import DayTransform, HourTransform
from pyiceberg.types import IntegerType, LongType, NestedField, StringType, StructType, TimestamptzType

from e2e.support import ManagedTable, OwnedNames, drop_table, wait_until

if TYPE_CHECKING:
    import httpx
    from pyarrow import fs
    from temporalio.client import Client

    from e2e.support import CleanupStack, OwnedCatalog, PlatformApi, TemporalSession

pytestmark = pytest.mark.full

SCHEMA = Schema(
    NestedField(1, "order_id", IntegerType(), required=True),
    NestedField(2, "customer_id", LongType(), required=False),
    NestedField(3, "order_ts", TimestamptzType(), required=False),
    NestedField(4, "shipping", StructType(NestedField(5, "city", StringType(), required=False)), required=False),
)
DAILY = PartitionSpec(PartitionField(source_id=3, field_id=1000, transform=DayTransform(), name="order_ts_day"))
FIRST_ROWS = pa.schema(
    [
        pa.field("order_id", pa.int32(), nullable=False),
        pa.field("customer_id", pa.int64()),
        pa.field("order_ts", pa.timestamp("us", tz="UTC")),
        pa.field("shipping", pa.struct([pa.field("city", pa.string())])),
    ]
)
EVOLVED_ROWS = pa.schema(
    [
        pa.field("order_id", pa.int64()),
        pa.field("customer", pa.int64()),
        pa.field("order_ts", pa.timestamp("us", tz="UTC")),
        pa.field("shipping", pa.struct([pa.field("city", pa.string()), pa.field("zip", pa.string())])),
    ]
)
WAIT_SECONDS = 180


@dataclass(frozen=True)
class _Evolved:
    table: ManagedTable
    uuid: str
    empty_metrics: dict[str, Any]
    unmanaged_uuid: str


def _append(owned: OwnedCatalog, table: ManagedTable, schema: pa.Schema, row: dict[str, Any]) -> None:
    owned.iceberg.load_table(table.identifier).append(pa.Table.from_pylist([row], schema=schema))


def _current_metrics(platform: PlatformApi, uuid: str, newer_than: str | None = None) -> dict[str, Any]:
    def observed() -> dict[str, Any]:
        current = platform.get(f"/v1/tables/{uuid}/metrics/current")
        if current["observed_at"] is None or current["observed_at"] == newer_than:
            raise AssertionError(current)
        return current

    return wait_until(observed, timeout=WAIT_SECONDS, interval=3, what=f"metrics of {uuid} observed")


@pytest.fixture(scope="module")
def evolved(
    platform: PlatformApi,
    s3: fs.S3FileSystem,
    temporal: TemporalSession[Client],
    owned_catalog: OwnedCatalog,
    suffix: str,
    module_cleanup: CleanupStack,
) -> _Evolved:
    """Manage the table while empty, then write, evolve and repartition it as the module docstring says."""
    table = ManagedTable.create(
        platform=platform,
        iceberg=owned_catalog.iceberg,
        s3=s3,
        temporal=temporal,
        cleanup=module_cleanup,
        catalog=owned_catalog.name,
        namespace=OwnedNames.namespace(suffix, "information"),
        name="tm_e2e_orders",
        schema=SCHEMA,
        partition_spec=DAILY,
        policy=(OwnedNames.maintenance_policy(suffix, "information"), "e2e: dry run", lambda b: {**b, "dry_run": True}),
        discovery_policy=OwnedNames.discovery_policy(suffix, "information"),
    )
    uuid = table.wait_until_managed(platform)
    empty = _current_metrics(platform, uuid)

    moment = datetime(2026, 11, 24, 8, tzinfo=UTC)
    _append(
        owned_catalog,
        table,
        FIRST_ROWS,
        {"order_id": 1, "customer_id": 7, "order_ts": moment, "shipping": {"city": "Taipei"}},
    )
    loaded = owned_catalog.iceberg.load_table(table.identifier)
    with loaded.update_schema() as update:
        update.rename_column("customer_id", "customer")
        update.update_column("order_id", field_type=LongType(), required=False)
        update.add_column(("shipping", "zip"), StringType())
    second = {"order_id": 2, "customer": 8, "order_ts": moment, "shipping": {"city": "Tainan", "zip": "700"}}
    _append(owned_catalog, table, EVOLVED_ROWS, second)
    with owned_catalog.iceberg.load_table(table.identifier).update_spec() as spec:
        spec.remove_field("order_ts_day")
        spec.add_field("order_ts", HourTransform(), "order_ts_hour")
    _append(owned_catalog, table, EVOLVED_ROWS, {**second, "order_id": 3})

    plain = (table.namespace, "plain")
    owned_catalog.iceberg.create_table(plain, SCHEMA)
    module_cleanup.push(f"drop {'.'.join(plain)}", lambda: drop_table(owned_catalog.iceberg, s3, plain))
    unmanaged = wait_until(
        lambda: (found := platform.table(owned_catalog.name, *plain)) and found["uuid"],
        timeout=WAIT_SECONDS,
        interval=3,
        what=f"{'.'.join(plain)} recorded",
    )
    return _Evolved(table=table, uuid=uuid, empty_metrics=empty, unmanaged_uuid=str(unmanaged))


def _catalog_table(table: ManagedTable) -> str:
    return f"/v1/catalogs/{table.catalog}/namespaces/{table.namespace}/tables/{table.name}"


def test_the_metrics_match_the_table_and_the_exporter_shows_them(
    api: httpx.Client, platform: PlatformApi, owned_catalog: OwnedCatalog, evolved: _Evolved
):
    """Empty, every count is 0; after a reconcile they match the snapshot's totals, and the exporter prints 17 samples.

    The totals come from the snapshot summary: PyIceberg's ``inspect.files()`` decodes every file's bounds with
    the current schema, so it cannot read the files written while ``order_id`` was a 4-byte int.
    """
    assert set(evolved.empty_metrics["metrics"].values()) == {0}, evolved.empty_metrics
    reply = api.post(f"/v1/tables/{evolved.uuid}/reconcile")
    assert reply.status_code == 202, reply.text
    table = owned_catalog.iceberg.load_table(evolved.table.identifier)
    snapshot = table.current_snapshot()
    assert snapshot is not None and snapshot.summary is not None
    totals = {
        key: int(str(snapshot.summary[key])) for key in ("total-data-files", "total-records", "total-delete-files")
    }

    def matching() -> dict[str, Any]:
        current = _current_metrics(platform, evolved.uuid, evolved.empty_metrics["observed_at"])
        if current["metrics"]["data_files"] != totals["total-data-files"]:
            raise AssertionError(current)
        return current["metrics"]

    metrics = wait_until(matching, timeout=WAIT_SECONDS, interval=3, what="metrics after the reconcile")
    assert metrics["data_records"] == totals["total-records"]
    deletes = ("position_delete_files", "equality_delete_files", "deletion_vectors")
    assert sum(metrics[key] for key in deletes) == totals["total-delete-files"]
    assert metrics["snapshots"] == len(table.snapshots())

    exported = api.get("/v1/table-metrics")
    assert exported.status_code == 200, exported.text
    samples = [
        line
        for line in exported.text.splitlines()
        if f'table_uuid="{evolved.uuid}"' in line and not line.startswith("#")
    ]
    assert len(samples) == 17, samples
    assert any(line.startswith("iceberg_table_info{") and line.endswith(" 1") for line in samples), samples
    [data_files] = [line for line in samples if line.startswith("iceberg_table_files{") and 'content="data"' in line]
    assert data_files.rsplit(" ", 1)[1] == str(totals["total-data-files"])

    unmanaged = platform.get(f"/v1/tables/{evolved.unmanaged_uuid}/metrics/current")
    assert (unmanaged["observed_at"], unmanaged["metrics"]) == (None, None)
    unknown = api.get("/v1/tables/00000000-0000-4000-8000-000000000000/metrics/current")
    assert unknown.status_code == 404, unknown.text


def test_the_table_record_and_the_catalog_answer_for_the_table(
    platform: PlatformApi, owned_catalog: OwnedCatalog, evolved: _Evolved
):
    """The record holds what decided it is managed and priority P3; a dry-run table attempted no operation.

    ``operation_states`` lists only the operations ever attempted, so it is empty here.
    """
    record = platform.get(f"/v1/tables/{evolved.uuid}")
    assert record["operation_states"] == {}
    assert record["decided_by"] == {
        "policy_id": evolved.table.discovery_policy["id"],
        "policy_version": 1,
        "rule_position": 1,
    }
    assert record["priority"] == "P3"

    table = owned_catalog.iceberg.load_table(evolved.table.identifier)
    held = platform.get(_catalog_table(evolved.table))
    assert held["uuid"] == str(table.metadata.table_uuid)
    assert held["current_snapshot_id"] == str(table.metadata.current_snapshot_id)
    assert {snapshot["id"] for snapshot in held["snapshots"]} == {str(s.snapshot_id) for s in table.snapshots()}
    assert held["properties"] == dict(table.properties)


def test_schema_versions_are_compared_by_field_id(api: httpx.Client, platform: PlatformApi, evolved: _Evolved):
    """Version 1 renamed one column, widened and loosened one, and added one nested column; version 0 has no base."""
    versions = platform.get(f"{_catalog_table(evolved.table)}/schema-versions")
    assert versions["current_schema_id"] == 1
    newest, oldest = versions["versions"]
    assert (newest["schema_id"], newest["previous_schema_id"], newest["current"]) == (1, 0, True)
    assert newest["changes"] == {
        "added": 1,
        "removed": 0,
        "renamed": 1,
        "type_changed": 1,
        "nullability_changed": 1,
        "doc_changed": 0,
    }
    assert (oldest["schema_id"], oldest["changes"]) == (0, None)

    comparison = platform.get(f"{_catalog_table(evolved.table)}/schema-versions/1/comparison")
    rows = {tuple(row["path"]): row for row in comparison["fields"]}
    assert (rows[("customer",)]["changes"], rows[("customer",)]["previous_path"]) == (["renamed"], ["customer_id"])
    assert rows[("order_id",)]["changes"] == ["type_changed", "nullability_changed"]
    assert (rows[("shipping", "zip")]["changes"], rows[("shipping", "zip")]["depth"]) == (["added"], 1)
    assert [rows[path]["changes"] for path in (("order_ts",), ("shipping",), ("shipping", "city"))] == [[], [], []]
    unknown = api.get(f"{_catalog_table(evolved.table)}/schema-versions/1/comparison", params={"base": 9})
    assert unknown.status_code == 404, unknown.text
    first = platform.get(f"{_catalog_table(evolved.table)}/schema-versions/0/comparison")
    assert first["base_schema_id"] is None


def test_partition_spec_versions_pair_a_changed_transform(platform: PlatformApi, evolved: _Evolved):
    """The daily field removed and the hourly one added on the same column are one transform change."""
    versions = platform.get(f"{_catalog_table(evolved.table)}/partition-spec-versions")
    assert versions["default_spec_id"] == 1
    assert [version["spec_id"] for version in versions["versions"]] == [1, 0]
    assert versions["versions"][0]["changes"]["transform_changed"] == 1
    [row] = platform.get(f"{_catalog_table(evolved.table)}/partition-spec-versions/1/comparison")["fields"]
    assert row["changes"] == ["transform_changed"]
    assert (row["previous_transform"], row["transform"]) == ("day", "hour")
    assert (row["previous_expression"], row["expression"]) == ("day(order_ts)", "hour(order_ts)")


def test_each_commit_carries_the_schema_it_was_written_with(platform: PlatformApi, evolved: _Evolved):
    """Newest first: two commits on the evolved schema, the first on version 0."""
    commits = platform.get(f"/v1/tables/{evolved.uuid}/commits")
    assert [commit["schema_id"] for commit in commits["items"]] == [1, 1, 0]
    assert commits["truncated"] is False
