from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pyarrow as pa
import pytest
from adapter.outbound.catalog.pyiceberg import ReadCatalogPyIcebergGateway
from application.port.outbound.catalog.read_catalog import (
    ReadCatalogGatewayListInput,
    ReadCatalogGatewayTableRef,
)
from application.service.catalog.table_observation_from_gateway import (
    table_observation_from_gateway,
)
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
def gateway(catalog: SqlCatalog) -> ReadCatalogPyIcebergGateway:
    return ReadCatalogPyIcebergGateway(lambda name: catalog)


def _ref(namespace: str = "db", table: str = "events") -> ReadCatalogGatewayTableRef:
    return ReadCatalogGatewayTableRef(CATALOG, namespace, table)


def _partitioned(catalog: SqlCatalog):
    catalog.create_namespace("db")
    spec = PartitionSpec(
        PartitionField(2, 1000, DayTransform(), "ts_day"),
        PartitionField(1, 1001, BucketTransform(4), "id_bucket"),
    )
    return catalog.create_table("db.events", SCHEMA, partition_spec=spec)


def test_observe_partitioned_table_groups_by_day_and_bucket(
    catalog: SqlCatalog, gateway: ReadCatalogPyIcebergGateway
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
    keys = [(p["spec_id"], tuple(p["values"])) for p in observation.partitions]
    assert len(keys) == len(set(keys))
    assert all(isinstance(v, int) for p in observation.partitions for v in p["values"])
    assert {p["values"][0] for p in observation.partitions} == {day1, day1 + 1}
    assert sum(p["data_file_count"] for p in observation.partitions) >= 4
    assert all(p["total_data_file_size_bytes"] > 0 for p in observation.partitions)
    assert all(p["position_delete_file_count"] == 0 for p in observation.partitions)
    assert [p["values"] for p in observation.partitions] == sorted(
        (p["values"] for p in observation.partitions), key=repr
    )
    id1_day1 = next(p for p in observation.partitions if p["values"][0] == day1 + 1)
    assert id1_day1["data_file_count"] == 1
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
    catalog: SqlCatalog, gateway: ReadCatalogPyIcebergGateway
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
    catalog: SqlCatalog, gateway: ReadCatalogPyIcebergGateway
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
    catalog: SqlCatalog, gateway: ReadCatalogPyIcebergGateway
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
    catalog: SqlCatalog, gateway: ReadCatalogPyIcebergGateway
) -> None:
    table = _partitioned(catalog)
    table.append(_rows([1, 2, 3], day=1))

    observation = gateway.observe_table(_ref())
    assert observation is not None
    domain = table_observation_from_gateway(observation)

    assert domain.table_uuid == str(table.metadata.table_uuid)
    assert domain.specs[0].fields[0].source_column == "ts"
    assert domain.snapshots[0].committed_at.tzinfo is not None
    assert len(domain.partitions) >= 1


def test_load_table_returns_metadata_uuid(
    catalog: SqlCatalog, gateway: ReadCatalogPyIcebergGateway
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
    catalog: SqlCatalog, gateway: ReadCatalogPyIcebergGateway
) -> None:
    catalog.create_namespace("db")

    assert gateway.load_table(_ref(table="nope")) is None
    assert gateway.observe_table(_ref(table="nope")) is None


def test_list_tables_with_and_without_namespace(
    catalog: SqlCatalog, gateway: ReadCatalogPyIcebergGateway
) -> None:
    catalog.create_namespace("db")
    catalog.create_namespace(("db", "inner"))
    catalog.create_namespace("other")
    catalog.create_table("db.events", SCHEMA)
    catalog.create_table("db.inner.deep", SCHEMA)
    catalog.create_table("other.x", SCHEMA)

    everything = gateway.list_tables(ReadCatalogGatewayListInput(CATALOG))
    scoped = gateway.list_tables(ReadCatalogGatewayListInput(CATALOG, "db.inner"))

    assert [(r.namespace, r.table) for r in everything] == [
        ("db", "events"),
        ("db.inner", "deep"),
        ("other", "x"),
    ]
    assert {r.catalog for r in everything} == {CATALOG}
    assert [(r.namespace, r.table) for r in scoped] == [("db.inner", "deep")]


def test_list_tables_of_missing_namespace_is_empty(
    gateway: ReadCatalogPyIcebergGateway,
) -> None:
    assert gateway.list_tables(ReadCatalogGatewayListInput(CATALOG, "ghost")) == []


def _failing_catalog(fail_on: str) -> MagicMock:
    stub = MagicMock(spec=Catalog)
    stub.list_namespaces.side_effect = (
        ServerError("boom") if fail_on == "list_namespaces" else None
    )
    if fail_on != "list_namespaces":
        stub.list_namespaces.side_effect = None
        stub.list_namespaces.return_value = [("db",)]
    stub.list_tables.side_effect = ServerError("boom")
    stub.load_table.side_effect = ServerError("boom")
    return stub


@pytest.mark.parametrize("fail_on", ["list_namespaces", "list_tables"])
def test_catalog_wide_listing_propagates_transient_errors(fail_on: str) -> None:
    gateway = ReadCatalogPyIcebergGateway(lambda name: _failing_catalog(fail_on))

    with pytest.raises(ServerError):
        gateway.list_tables(ReadCatalogGatewayListInput(CATALOG))


def test_scoped_listing_and_loading_propagate_transient_errors() -> None:
    gateway = ReadCatalogPyIcebergGateway(lambda name: _failing_catalog("x"))

    with pytest.raises(ServerError):
        gateway.list_tables(ReadCatalogGatewayListInput(CATALOG, "db"))
    with pytest.raises(ServerError):
        gateway.load_table(_ref())
    with pytest.raises(ServerError):
        gateway.observe_table(_ref())
