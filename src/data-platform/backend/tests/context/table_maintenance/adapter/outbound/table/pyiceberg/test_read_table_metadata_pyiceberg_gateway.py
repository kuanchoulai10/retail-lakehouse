"""Test the PyIceberg gateway against a real SQL catalog with generated tables."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

import pyarrow as pa
import pytest
from pyiceberg.catalog import Catalog
from pyiceberg.catalog.sql import SqlCatalog
from pyiceberg.exceptions import (
    ForbiddenError,
    NoSuchNamespaceError,
    RESTError,
    ServerError,
    UnauthorizedError,
)
from pyiceberg.partitioning import PartitionField, PartitionSpec
from pyiceberg.schema import Schema
from pyiceberg.transforms import BucketTransform, DayTransform, IdentityTransform
from pyiceberg.types import LongType, NestedField, StringType, TimestampType

from context.table_maintenance.adapter.outbound.table.pyiceberg import (
    ReadTableMetadataPyIcebergGateway,
    commit_page_from_table,
)
from context.table_maintenance.application.port.outbound.table import (
    CatalogAccessDeniedError,
    CatalogNotFoundError,
    ReadTableMetadataGatewayListInput,
    TableCommitSelection,
    TableMetadataRef,
)
from context.table_maintenance.application.service.table import (
    table_observation_from_gateway,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pyiceberg.table import Table

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
            "ts": [datetime(2024, 1, day, 10, tzinfo=UTC).replace(tzinfo=None)] * len(ids),
            "region": ["eu"] * len(ids),
        },
        schema=ARROW,
    )


@pytest.fixture
def catalog(tmp_path: Path) -> SqlCatalog:
    """Provide a SQLite-backed Iceberg catalog in a temporary directory."""
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    return SqlCatalog(
        CATALOG,
        uri=f"sqlite:///{tmp_path / 'catalog.db'}",
        warehouse=f"file://{warehouse}",
    )


@pytest.fixture
def gateway(catalog: SqlCatalog) -> ReadTableMetadataPyIcebergGateway:
    """Provide a gateway that reads from the test catalog."""
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
    """Observing a partitioned table groups its data files by day and bucket partition."""
    table = _partitioned(catalog)
    table.append(_rows([1, 2, 3, 4, 5, 6], day=1))
    table.append(_rows([1, 2], day=1))
    table.append(_rows([1], day=2))

    observation = gateway.observe_table(_ref())

    assert observation is not None
    assert observation.current_snapshot_id == table.refresh().current_snapshot().snapshot_id
    day1 = (datetime(2024, 1, 1) - datetime(1970, 1, 1)).days
    bucket = BucketTransform(4).transform(LongType())
    expected: Counter[tuple[int, int]] = Counter()
    for day, ids in ((day1, [1, 2, 3, 4, 5, 6]), (day1, [1, 2]), (day1 + 1, [1])):
        for key in {(day, cast("int", bucket(i))) for i in ids}:
            expected[key] += 1
    assert {tuple(p["values"]): p["data_file_count"] for p in observation.partitions} == expected
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


def test_observe_counts_data_records_per_partition(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    """Each partition carries the record count of its data files and no delete records."""
    catalog.create_namespace("db")
    spec = PartitionSpec(PartitionField(2, 1000, DayTransform(), "ts_day"))
    table = catalog.create_table("db.events", SCHEMA, partition_spec=spec)
    table.append(_rows([1, 2, 3], day=1))
    table.append(_rows([4, 5], day=2))

    observation = gateway.observe_table(_ref())

    assert observation is not None
    day1 = (datetime(2024, 1, 1) - datetime(1970, 1, 1)).days
    assert {p["values"][0]: p["data_record_count"] for p in observation.partitions} == {day1: 3, day1 + 1: 2}
    assert all(p["position_delete_record_count"] == 0 for p in observation.partitions)
    assert all(p["equality_delete_record_count"] == 0 for p in observation.partitions)
    assert all(p["deletion_vector_count"] == 0 for p in observation.partitions)


def test_observe_counts_manifest_entries(catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway) -> None:
    """Each manifest of two appends has one added entry and no existing or deleted ones."""
    catalog.create_namespace("db")
    table = catalog.create_table("db.events", SCHEMA)
    table.append(_rows([1], day=1))
    table.append(_rows([2], day=1))

    observation = gateway.observe_table(_ref())

    assert observation is not None
    assert len(observation.manifests) == 2
    assert all(
        (m["added_entries"], m["existing_entries"], m["deleted_entries"]) == (1, 0, 0) for m in observation.manifests
    )


def test_observe_records_when_each_partition_was_last_written(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    """Each partition's last write is the commit time of the newest snapshot that added a file to it."""
    catalog.create_namespace("db")
    spec = PartitionSpec(PartitionField(2, 1000, DayTransform(), "ts_day"))
    table = catalog.create_table("db.events", SCHEMA, partition_spec=spec)
    table.append(_rows([1], day=1))
    table.append(_rows([2], day=2))
    table.append(_rows([3], day=1))
    snapshots = table.refresh().metadata.snapshots

    observation = gateway.observe_table(_ref())

    assert observation is not None
    day1 = (datetime(2024, 1, 1) - datetime(1970, 1, 1)).days
    committed = [datetime.fromtimestamp(s.timestamp_ms / 1000, tz=UTC).isoformat() for s in snapshots]
    assert {p["values"][0]: p["last_written_at"] for p in observation.partitions} == {
        day1: committed[2],
        day1 + 1: committed[1],
    }


def test_observe_unpartitioned_table_has_one_row_with_empty_values(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    """An unpartitioned table is observed as one partition with empty values."""
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
    """A table without a snapshot is observed with no snapshot id and no partitions."""
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
    """After partition spec evolution the observation carries partitions of both spec ids."""
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
    """An observation converts to the domain model with the table uuid and spec fields."""
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


def test_load_table_returns_metadata_uuid(catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway) -> None:
    """Loading a table returns its catalog, namespace, name and uuid."""
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


def test_load_table_without_snapshots_has_no_last_commit(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    """A table never committed to has no last commit."""
    catalog.create_namespace("db")
    catalog.create_table("db.events", SCHEMA)

    loaded = gateway.load_table(_ref())

    assert loaded is not None
    assert loaded.last_committed_at is None


def test_load_table_carries_the_newest_commit_time(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    """Loading a table carries its newest snapshot's commit time as an aware ISO timestamp."""
    table = _partitioned(catalog)
    for day in (1, 2):
        table.append(_rows([day], day=day))
    newest_ms = max(s.timestamp_ms for s in catalog.load_table("db.events").metadata.snapshots)

    loaded = gateway.load_table(_ref())

    assert loaded is not None
    assert loaded.last_committed_at is not None
    assert datetime.fromisoformat(loaded.last_committed_at) == datetime.fromtimestamp(newest_ms / 1000, tz=UTC)


def test_missing_table_returns_none(catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway) -> None:
    """Loading or observing a table that does not exist returns None."""
    catalog.create_namespace("db")

    assert gateway.load_table(_ref(table="nope")) is None
    assert gateway.observe_table(_ref(table="nope")) is None


def test_list_tables_with_and_without_namespace(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    """Listing tables covers the whole catalog, or only the given namespace."""
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
    """Listing a namespace that does not exist returns no tables."""
    assert gateway.list_tables(ReadTableMetadataGatewayListInput(CATALOG, "ghost")) == []


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


@pytest.mark.parametrize("fail_on", ["list_namespaces", "nested_list_namespaces", "list_tables"])
def test_catalog_wide_listing_propagates_transient_errors(fail_on: str) -> None:
    """A transient catalog error during a catalog-wide listing is raised, not swallowed."""
    gateway = ReadTableMetadataPyIcebergGateway(lambda name: _failing_catalog(fail_on))

    with pytest.raises(ServerError):
        gateway.list_tables(ReadTableMetadataGatewayListInput(CATALOG))


def test_scoped_listing_and_loading_propagate_transient_errors() -> None:
    """A transient error while listing a namespace or loading a table is raised."""
    gateway = ReadTableMetadataPyIcebergGateway(lambda name: _failing_catalog("list_tables"))

    with pytest.raises(ServerError):
        gateway.list_tables(ReadTableMetadataGatewayListInput(CATALOG, "db"))
    with pytest.raises(ServerError):
        gateway.load_table(_ref())
    with pytest.raises(ServerError):
        gateway.observe_table(_ref())


def test_list_commits_newest_first_with_limit(catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway) -> None:
    """Commits are listed newest first and cut at the limit, marked as truncated."""
    table = _partitioned(catalog)
    for day in (1, 2, 3):
        table.append(_rows([day], day=day))
    snapshots = catalog.load_table("db.events").metadata.snapshots

    page = gateway.list_commits(_ref(), TableCommitSelection(limit=2))

    assert page is not None
    assert page.table_uuid == str(table.metadata.table_uuid)
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


def test_list_commits_carry_the_schema_id_each_was_written_with(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    """A commit made before a schema change reads the old schema id and the next one the new id."""
    catalog.create_namespace("db")
    table = catalog.create_table("db.events", SCHEMA)
    table.append(_rows([1], day=1))
    with catalog.load_table("db.events").update_schema() as update:
        update.add_column("note", StringType())
    evolved = catalog.load_table("db.events")
    evolved.append(
        pa.table(
            {
                "id": [2],
                "ts": [datetime(2024, 1, 2, 10)],
                "region": ["eu"],
                "note": ["x"],
            },
            schema=ARROW.append(pa.field("note", pa.string())),
        )
    )

    page = gateway.list_commits(_ref(), TableCommitSelection(limit=10))

    assert page is not None
    assert [c["schema_id"] for c in page.commits] == [1, 0]


def _v1_table_with_a_schema_change(catalog: SqlCatalog) -> Table:
    catalog.create_namespace("db")
    table = catalog.create_table("db.events", SCHEMA, properties={"format-version": "1"})
    table.append(_rows([1], day=1))
    with catalog.load_table("db.events").update_schema() as update:
        update.add_column("note", StringType())
    evolved = catalog.load_table("db.events")
    evolved.append(
        pa.table(
            {"id": [2], "ts": [datetime(2024, 1, 2, 10)], "region": ["eu"], "note": ["x"]},
            schema=ARROW.append(pa.field("note", pa.string())),
        )
    )
    return catalog.load_table("db.events")


def test_list_commits_of_a_format_v1_table_carry_their_schema_ids(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    """A real format v1 table records the schema id on each snapshot, and each commit carries it."""
    table = _v1_table_with_a_schema_change(catalog)
    assert table.metadata.format_version == 1

    page = gateway.list_commits(_ref(), TableCommitSelection(limit=10))

    assert page is not None
    assert [c["schema_id"] for c in page.commits] == [1, 0]


def test_a_v1_snapshot_without_a_schema_id_maps_to_none_and_keeps_the_key(catalog: SqlCatalog) -> None:
    """Older v1 writers left ``schema-id`` off a snapshot; the commit then carries the key with None."""
    table = _v1_table_with_a_schema_change(catalog)
    snapshots = [snapshot.model_copy(update={"schema_id": None}) for snapshot in table.metadata.snapshots]
    without_ids = cast("Table", SimpleNamespace(metadata=table.metadata.model_copy(update={"snapshots": snapshots})))

    page = commit_page_from_table(without_ids, TableCommitSelection(limit=10))

    assert [c["schema_id"] for c in page.commits] == [None, None]


def test_every_commit_carries_the_schema_id_key(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    """The mapper writes ``schema_id`` on every commit, so the service can read it without a default."""
    _v1_table_with_a_schema_change(catalog)

    page = gateway.list_commits(_ref(), TableCommitSelection(limit=10))

    assert page is not None
    assert page.commits
    assert all("schema_id" in commit for commit in page.commits)


def test_list_commits_since(catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway) -> None:
    """Listing commits since a time returns only the later commits and is not truncated when all fit."""
    table = _partitioned(catalog)
    for day in (1, 2, 3):
        table.append(_rows([day], day=day))
    everything = gateway.list_commits(_ref(), TableCommitSelection(limit=10))
    assert everything is not None
    assert everything.truncated is False
    second = datetime.fromisoformat(everything.commits[1]["committed_at"])

    page = gateway.list_commits(_ref(), TableCommitSelection(limit=10, since=second))

    assert page is not None
    assert len(page.commits) == 2
    assert page.truncated is False


def test_list_commits_before(catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway) -> None:
    """Listing commits before a time leaves out the commit made at that time and every later one."""
    table = _partitioned(catalog)
    for day in (1, 2, 3):
        table.append(_rows([day], day=day))
    everything = gateway.list_commits(_ref(), TableCommitSelection(limit=10))
    assert everything is not None
    newest = datetime.fromisoformat(everything.commits[0]["committed_at"])

    page = gateway.list_commits(_ref(), TableCommitSelection(limit=10, before=newest))

    assert page is not None
    assert [c["snapshot_id"] for c in page.commits] == [c["snapshot_id"] for c in everything.commits[1:]]


def test_list_commits_by_writer(catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway) -> None:
    """Listing commits by writer keeps only that writer's commits, before the limit is applied."""
    table = _partitioned(catalog)
    for day in (1, 2):
        table.append(_rows([day], day=day))

    unknown = gateway.list_commits(_ref(), TableCommitSelection(limit=1, writer="unknown"))
    spark = gateway.list_commits(_ref(), TableCommitSelection(limit=1, writer="spark"))

    assert unknown is not None
    assert len(unknown.commits) == 1
    assert unknown.truncated is True
    assert spark is not None
    assert spark.commits == []
    assert spark.truncated is False


def test_reads_return_none_for_missing_table(catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway) -> None:
    """List commits returns None for a missing table."""
    catalog.create_namespace("db")
    ref = _ref(table="nope")

    assert gateway.list_commits(ref, TableCommitSelection(limit=5)) is None


def test_unknown_catalog_raises_catalog_not_found() -> None:
    """A catalog the server rejects by name is an error, never an empty listing."""

    def factory(name: str) -> Catalog:
        raise RESTError("RESTError: unknown warehouse")

    gateway = ReadTableMetadataPyIcebergGateway(factory)

    with pytest.raises(CatalogNotFoundError):
        gateway.list_tables(ReadTableMetadataGatewayListInput("nope"))
    with pytest.raises(CatalogNotFoundError):
        gateway.list_tables(ReadTableMetadataGatewayListInput("nope", "db"))
    with pytest.raises(CatalogNotFoundError):
        gateway.load_table(_ref())


@pytest.mark.parametrize("refusal", [ForbiddenError, UnauthorizedError])
def test_forbidden_on_open_is_access_denied(refusal: type[RESTError]) -> None:
    """A catalog whose opening the server refuses for the credential is CatalogAccessDeniedError on every read."""

    def factory(name: str) -> Catalog:
        raise refusal("refused")

    gateway = ReadTableMetadataPyIcebergGateway(factory)

    for read in (
        lambda: gateway.catalog_exists("secret"),
        lambda: gateway.namespace_exists("secret", "db"),
        lambda: gateway.list_tables(ReadTableMetadataGatewayListInput("secret")),
        lambda: gateway.load_table(_ref()),
        lambda: gateway.observe_table(_ref()),
        lambda: gateway.list_commits(_ref(), TableCommitSelection(limit=1)),
    ):
        with pytest.raises(CatalogAccessDeniedError, match="cannot read catalog"):
            read()


def _refusing_catalog(refusal: type[RESTError]) -> MagicMock:
    stub = MagicMock(spec=Catalog)
    stub.list_namespaces.side_effect = refusal("refused")
    stub.list_tables.side_effect = refusal("refused")
    stub.load_table.side_effect = refusal("refused")
    stub.namespace_exists.side_effect = refusal("refused")
    return stub


@pytest.mark.parametrize("refusal", [ForbiddenError, UnauthorizedError])
def test_forbidden_on_listing_and_loading_is_access_denied(refusal: type[RESTError]) -> None:
    """A refusal after the catalog opened (listing, loading, a namespace check) is CatalogAccessDeniedError."""
    gateway = ReadTableMetadataPyIcebergGateway(lambda name: _refusing_catalog(refusal))

    for read in (
        lambda: gateway.namespace_exists(CATALOG, "db"),
        lambda: gateway.list_tables(ReadTableMetadataGatewayListInput(CATALOG)),
        lambda: gateway.list_tables(ReadTableMetadataGatewayListInput(CATALOG, "db")),
        lambda: gateway.load_table(_ref()),
    ):
        with pytest.raises(CatalogAccessDeniedError, match=f"cannot read catalog {CATALOG}$"):
            read()


def test_catalog_exists_opens_the_catalog(gateway: ReadTableMetadataPyIcebergGateway) -> None:
    """A catalog that opens exists, even when it holds nothing."""
    assert gateway.catalog_exists(CATALOG) is True


def test_catalog_exists_reads_the_catalog_live_after_opening_it() -> None:
    """An opened catalog is asked for its top-level namespaces, so a cached catalog cannot hide a deletion."""
    stub = MagicMock(spec=Catalog)
    stub.list_namespaces.return_value = []
    gateway = ReadTableMetadataPyIcebergGateway(lambda name: stub)

    assert gateway.catalog_exists(CATALOG) is True
    stub.list_namespaces.assert_called_once_with()


def test_catalog_exists_is_false_when_the_live_read_finds_no_catalog() -> None:
    """A catalog that opens but answers 404 to its top-level listing was deleted since it was opened."""
    stub = MagicMock(spec=Catalog)
    stub.list_namespaces.side_effect = NoSuchNamespaceError("catalog gone")

    assert ReadTableMetadataPyIcebergGateway(lambda name: stub).catalog_exists(CATALOG) is False


def test_catalog_wide_listing_whose_top_level_read_finds_no_catalog_raises_catalog_not_found() -> None:
    """A catalog deleted since it was opened reads as not found, as catalog_exists reads it; a namespace stays empty."""
    stub = MagicMock(spec=Catalog)
    stub.list_namespaces.side_effect = NoSuchNamespaceError("catalog gone")
    stub.list_tables.side_effect = NoSuchNamespaceError("catalog gone")
    gateway = ReadTableMetadataPyIcebergGateway(lambda name: stub)

    with pytest.raises(CatalogNotFoundError, match=f"{CATALOG}"):
        gateway.list_tables(ReadTableMetadataGatewayListInput(CATALOG))
    assert gateway.list_tables(ReadTableMetadataGatewayListInput(CATALOG, "db")) == []


@pytest.mark.parametrize("refusal", [ForbiddenError, UnauthorizedError])
def test_catalog_exists_is_access_denied_when_the_live_read_is_refused(refusal: type[RESTError]) -> None:
    """A catalog that opens but refuses the credential its top-level listing raises CatalogAccessDeniedError."""
    gateway = ReadTableMetadataPyIcebergGateway(lambda name: _refusing_catalog(refusal))

    with pytest.raises(CatalogAccessDeniedError, match=f"cannot read catalog {CATALOG}$"):
        gateway.catalog_exists(CATALOG)


def test_catalog_exists_propagates_a_server_error_on_the_live_read() -> None:
    """A server error on the live read is not a missing catalog."""
    gateway = ReadTableMetadataPyIcebergGateway(lambda name: _failing_catalog("list_namespaces"))

    with pytest.raises(ServerError):
        gateway.catalog_exists(CATALOG)


def test_catalog_exists_is_false_for_an_unknown_catalog() -> None:
    """A catalog the server rejects by name does not exist."""

    def factory(name: str) -> Catalog:
        raise RESTError("RESTError: unknown warehouse")

    assert ReadTableMetadataPyIcebergGateway(factory).catalog_exists("nope") is False


def test_namespace_exists_reads_the_dotted_namespace() -> None:
    """The dotted namespace is split into its levels before PyIceberg is asked."""
    stub = MagicMock(spec=Catalog)
    stub.namespace_exists.return_value = True
    gateway = ReadTableMetadataPyIcebergGateway(lambda name: stub)

    assert gateway.namespace_exists(CATALOG, "sales.eu") is True
    stub.namespace_exists.assert_called_once_with(("sales", "eu"))


def test_namespace_exists_for_an_empty_and_a_missing_namespace(
    catalog: SqlCatalog, gateway: ReadTableMetadataPyIcebergGateway
) -> None:
    """An empty namespace exists, a parent of a nested one exists, and one never created does not."""
    catalog.create_namespace("db")
    catalog.create_namespace(("db", "inner"))

    assert gateway.namespace_exists(CATALOG, "db") is True
    assert gateway.namespace_exists(CATALOG, "db.inner") is True
    assert gateway.namespace_exists(CATALOG, "ghost") is False


def test_namespace_exists_in_an_unknown_catalog_raises_catalog_not_found() -> None:
    """A namespace of a catalog the server rejects by name raises CatalogNotFoundError."""

    def factory(name: str) -> Catalog:
        raise RESTError("RESTError: unknown warehouse")

    with pytest.raises(CatalogNotFoundError):
        ReadTableMetadataPyIcebergGateway(factory).namespace_exists("nope", "db")


def test_catalog_open_server_errors_still_propagate() -> None:
    """A server error while opening the catalog is not an unknown catalog."""

    def factory(name: str) -> Catalog:
        raise ServerError("boom")

    gateway = ReadTableMetadataPyIcebergGateway(factory)

    with pytest.raises(ServerError):
        gateway.list_tables(ReadTableMetadataGatewayListInput("lake"))
