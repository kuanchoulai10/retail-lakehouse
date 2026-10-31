from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

import pyarrow as pa
import pytest
from adapter.outbound.table.pyiceberg import ReadTableMetadataPyIcebergGateway
from application.port.outbound.table import (
    ReadTableMetadataGatewayListInput,
    TableMetadataRef,
)
from application.service.table import table_observation_from_gateway
from pyiceberg.catalog import Catalog
from pyiceberg.catalog.sql import SqlCatalog
from pyiceberg.exceptions import ServerError
from pyiceberg.partitioning import PartitionField, PartitionSpec
from pyiceberg.schema import Schema
from pyiceberg.transforms import BucketTransform, DayTransform, IdentityTransform
from pyiceberg.types import LongType, NestedField, StringType, TimestampType

if TYPE_CHECKING:
    from pathlib import Path

CATALOG = "lake"
SCHEMA = Schema(
    NestedField(1, "id", LongType(), required=False),
    NestedField(2, "ts", TimestampType(), required=False),
    NestedField(3, "region", StringType(), required=False),
)
ARROW = pa.schema(
    [
        pa.field("id", pa.int64()),
        pa.field("ts", pa.timestamp("us")),
        pa.field("region", pa.string()),
    ]
)


def _rows(ids: list[int], day: int) -> pa.Table:
    return pa.table(
        {
            "id": ids,
            "ts": [datetime(2024, 1, day, 10, tzinfo=UTC).replace(tzinfo=None)]
            * len(ids),
            "region": ["eu"] * len(ids),
        },
        schema=ARROW,
    )


@pytest.fixture
def catalog(tmp_path: Path) -> SqlCatalog:
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    return SqlCatalog(
        CATALOG,
        uri=f"sqlite:///{tmp_path / 'catalog.db'}",
        warehouse=f"file://{warehouse}",
    )


@pytest.fixture
def gateway(catalog: SqlCatalog) -> ReadTableMetadataPyIcebergGateway:
    return ReadTableMetadataPyIcebergGateway(lambda name: catalog)


def _ref(namespace: str = "db", table: str = "events") -> TableMetadataRef:
    return TableMetadataRef(CATALOG, namespace, table)


def _partitioned(catalog: SqlCatalog):
    catalog.create_namespace("db")
    spec = PartitionSpec(
        PartitionField(2, 1000, DayTransform(), "ts_day"),
        PartitionField(1, 1001, BucketTransform(4), "id_bucket"),
    )
    return catalog.create_table("db.events", SCHEMA, partition_spec=spec)


def test_observe_partitioned_table_groups_by_day_and_bucket(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    table = _partitioned(catalog)
    table.append(_rows([1, 2, 3, 4, 5, 6], day=1))
    table.append(_rows([1, 2], day=1))
    table.append(_rows([1], day=2))

    observation = gateway.observe_table(_ref())

    assert observation is not None
    assert (
        observation.current_snapshot_id
        == table.refresh().current_snapshot().snapshot_id
    )
    day1 = (datetime(2024, 1, 1) - datetime(1970, 1, 1)).days
    bucket = BucketTransform(4).transform(LongType())
    expected: Counter[tuple[int, int]] = Counter()
    for day, ids in ((day1, [1, 2, 3, 4, 5, 6]), (day1, [1, 2]), (day1 + 1, [1])):
        for key in {(day, cast("int", bucket(i))) for i in ids}:
            expected[key] += 1
    assert {
        tuple(p["values"]): p["data_file_count"] for p in observation.partitions
    } == expected
    assert len(observation.partitions) == len(expected)
    assert all(p["total_data_file_size_bytes"] > 0 for p in observation.partitions)
    assert all(p["position_delete_file_count"] == 0 for p in observation.partitions)
    assert all(p["equality_delete_file_count"] == 0 for p in observation.partitions)
    assert [p["values"] for p in observation.partitions] == sorted(
        (p["values"] for p in observation.partitions), key=repr
    )
    assert len(observation.manifests) == 3
    assert all(m["length_bytes"] > 0 for m in observation.manifests)
    assert len(observation.snapshots) == 3
    assert observation.specs[0]["fields"] == [
        {
            "field_id": 1000,
            "name": "ts_day",
            "source_column": "ts",
            "source_type": "timestamp",
            "transform": "day",
        },
        {
            "field_id": 1001,
            "name": "id_bucket",
            "source_column": "id",
            "source_type": "long",
            "transform": "bucket[4]",
        },
    ]


def test_observe_unpartitioned_table_has_one_row_with_empty_values(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    catalog.create_namespace("db")
    table = catalog.create_table("db.events", SCHEMA)
    table.append(_rows([1, 2], day=1))

    observation = gateway.observe_table(_ref())

    assert observation is not None
    assert len(observation.partitions) == 1
    assert observation.partitions[0]["values"] == []
    assert observation.partitions[0]["data_file_count"] == 1


def test_observe_table_without_snapshot_has_no_partitions(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    catalog.create_namespace("db")
    catalog.create_table("db.events", SCHEMA)

    observation = gateway.observe_table(_ref())

    assert observation is not None
    assert observation.current_snapshot_id is None
    assert observation.partitions == []
    assert observation.manifests == []
    assert observation.snapshots == []


def test_observe_after_spec_evolution_carries_both_spec_ids(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    catalog.create_namespace("db")
    table = catalog.create_table("db.events", SCHEMA)
    table.append(_rows([1], day=1))
    with table.update_spec() as update:
        update.add_field("region", IdentityTransform(), "region")
    table = catalog.load_table("db.events")
    table.append(_rows([2], day=1))

    observation = gateway.observe_table(_ref())

    assert observation is not None
    by_spec = {p["spec_id"]: p for p in observation.partitions}
    assert sorted(by_spec) == [0, 1]
    assert by_spec[0]["values"] == []
    assert by_spec[1]["values"] == ["eu"]
    assert {s["spec_id"] for s in observation.specs} == {0, 1}
    spec1 = next(s for s in observation.specs if s["spec_id"] == 1)
    assert spec1["fields"][0]["source_type"] == "string"
    assert spec1["fields"][0]["transform"] == "identity"


def test_observation_round_trips_through_the_domain_converter(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    table = _partitioned(catalog)
    table.append(_rows([1, 2, 3], day=1))

    observation = gateway.observe_table(_ref())
    assert observation is not None
    domain = table_observation_from_gateway(observation)

    assert domain.table_uuid == str(table.metadata.table_uuid)
    assert domain.specs[0].fields[0].source_column == "ts"
    assert domain.snapshots[0].committed_at.tzinfo is not None
    day1 = (datetime(2024, 1, 1) - datetime(1970, 1, 1)).days
    assert {(p.values, p.data_file_count) for p in domain.partitions} == {
        ((day1, 0), 1),
        ((day1, 3), 1),
    }


def test_load_table_returns_metadata_uuid(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    catalog.create_namespace("db")
    table = catalog.create_table("db.events", SCHEMA)

    loaded = gateway.load_table(_ref())

    assert loaded is not None
    assert loaded.table_uuid == str(table.metadata.table_uuid)
    assert (loaded.catalog, loaded.namespace, loaded.table) == (
        CATALOG,
        "db",
        "events",
    )


def test_missing_table_returns_none(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    catalog.create_namespace("db")

    assert gateway.load_table(_ref(table="nope")) is None
    assert gateway.observe_table(_ref(table="nope")) is None


def test_list_tables_with_and_without_namespace(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    catalog.create_namespace("db")
    catalog.create_namespace(("db", "inner"))
    catalog.create_namespace("other")
    catalog.create_table("db.events", SCHEMA)
    catalog.create_table("db.inner.deep", SCHEMA)
    catalog.create_table("other.x", SCHEMA)

    everything = gateway.list_tables(ReadTableMetadataGatewayListInput(CATALOG))
    scoped = gateway.list_tables(ReadTableMetadataGatewayListInput(CATALOG, "db.inner"))

    assert [(r.namespace, r.table) for r in everything] == [
        ("db", "events"),
        ("db.inner", "deep"),
        ("other", "x"),
    ]
    assert {r.catalog for r in everything} == {CATALOG}
    assert [(r.namespace, r.table) for r in scoped] == [("db.inner", "deep")]


def test_list_tables_of_missing_namespace_is_empty(
    gateway: ReadTableMetadataPyIcebergGateway,
) -> None:
    assert (
        gateway.list_tables(ReadTableMetadataGatewayListInput(CATALOG, "ghost")) == []
    )


def _failing_catalog(fail_on: str) -> MagicMock:
    def list_namespaces(namespace: tuple[str, ...] = ()) -> list[tuple[str, ...]]:
        if fail_on == "list_namespaces" and namespace == ():
            raise ServerError("boom")
        if fail_on == "nested_list_namespaces" and namespace == ("db",):
            raise ServerError("boom")
        return [("db",)] if namespace == () else []

    def list_tables(namespace: tuple[str, ...]) -> list[tuple[str, ...]]:
        if fail_on == "list_tables":
            raise ServerError("boom")
        return []

    stub = MagicMock(spec=Catalog)
    stub.list_namespaces.side_effect = list_namespaces
    stub.list_tables.side_effect = list_tables
    stub.load_table.side_effect = ServerError("boom")
    return stub


@pytest.mark.parametrize(
    "fail_on", ["list_namespaces", "nested_list_namespaces", "list_tables"]
)
def test_catalog_wide_listing_propagates_transient_errors(fail_on: str) -> None:
    gateway = ReadTableMetadataPyIcebergGateway(lambda name: _failing_catalog(fail_on))

    with pytest.raises(ServerError):
        gateway.list_tables(ReadTableMetadataGatewayListInput(CATALOG))


def test_scoped_listing_and_loading_propagate_transient_errors() -> None:
    gateway = ReadTableMetadataPyIcebergGateway(
        lambda name: _failing_catalog("list_tables")
    )

    with pytest.raises(ServerError):
        gateway.list_tables(ReadTableMetadataGatewayListInput(CATALOG, "db"))
    with pytest.raises(ServerError):
        gateway.load_table(_ref())
    with pytest.raises(ServerError):
        gateway.observe_table(_ref())


def test_describe_partitioned_table(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    table = _partitioned(catalog)
    table.append(_rows([1, 2], day=1))
    table.append(_rows([3], day=2))
    current = catalog.load_table("db.events")

    description = gateway.describe_table(_ref())

    assert description is not None
    assert description.table_uuid == str(current.metadata.table_uuid)
    assert description.format_version == current.metadata.format_version
    assert description.location == current.location()
    assert [f["name"] for f in description.schema_fields] == ["id", "ts", "region"]
    assert description.schema_fields[0] == {
        "field_id": 1,
        "name": "id",
        "type": "long",
        "required": False,
    }
    assert [f["name"] for f in description.specs[0]["fields"]] == [
        "ts_day",
        "id_bucket",
    ]
    assert description.snapshot_count == 2
    snapshot = current.current_snapshot()
    assert snapshot is not None
    assert description.current_snapshot_id == snapshot.snapshot_id
    assert description.current_summary["operation"] == "append"
    assert description.last_committed_at is not None
    assert datetime.fromisoformat(description.last_committed_at).tzinfo is not None


def test_describe_empty_table(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    catalog.create_namespace("db")
    catalog.create_table("db.events", SCHEMA)

    description = gateway.describe_table(_ref())

    assert description is not None
    assert description.current_snapshot_id is None
    assert description.snapshot_count == 0
    assert description.current_summary == {}
    assert description.last_committed_at is None


def test_list_commits_newest_first_with_limit(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    table = _partitioned(catalog)
    for day in (1, 2, 3):
        table.append(_rows([day], day=day))
    snapshots = catalog.load_table("db.events").metadata.snapshots

    page = gateway.list_commits(_ref(), since=None, limit=2)

    assert page is not None
    assert page.truncated is True
    assert [c["snapshot_id"] for c in page.commits] == [
        snapshots[2].snapshot_id,
        snapshots[1].snapshot_id,
    ]
    assert page.commits[0]["parent_id"] == snapshots[1].snapshot_id
    assert page.commits[0]["operation"] == "append"
    assert page.commits[0]["summary"]["operation"] == "append"
    assert page.commits[0]["writer"] == "unknown"
    assert datetime.fromisoformat(page.commits[0]["committed_at"]).tzinfo is not None


def test_list_commits_since(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    table = _partitioned(catalog)
    for day in (1, 2, 3):
        table.append(_rows([day], day=day))
    everything = gateway.list_commits(_ref(), since=None, limit=10)
    assert everything is not None
    assert everything.truncated is False
    second = everything.commits[1]["committed_at"]

    page = gateway.list_commits(_ref(), since=second, limit=10)

    assert page is not None
    assert len(page.commits) == 2
    assert page.truncated is False


def test_measure_storage_counts_files_kept_by_old_snapshots(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    table = _partitioned(catalog)
    table.append(_rows([1, 2], day=1))
    table.overwrite(_rows([5, 6], day=2))

    measure = gateway.measure_storage(_ref())

    assert measure is not None
    assert measure.current_files > 0
    assert measure.referenced_files > measure.current_files
    assert measure.referenced_bytes > measure.current_bytes > 0


def test_measure_storage_of_empty_table_is_zero(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    catalog.create_namespace("db")
    catalog.create_table("db.events", SCHEMA)

    measure = gateway.measure_storage(_ref())

    assert measure is not None
    assert (
        measure.current_bytes,
        measure.current_files,
        measure.referenced_bytes,
        measure.referenced_files,
    ) == (0, 0, 0, 0)


def test_reads_return_none_for_missing_table(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    catalog.create_namespace("db")
    ref = _ref(table="nope")

    assert gateway.describe_table(ref) is None
    assert gateway.list_commits(ref, since=None, limit=5) is None
    assert gateway.measure_storage(ref) is None
