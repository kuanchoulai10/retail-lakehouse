"""Test the table use cases against the in-memory tables repo."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from context.catalog.application.exceptions import ConflictError, NotFoundError, ValidationError
from context.catalog.application.port.inbound.table import (
    CreateTableUseCaseInput,
    DeleteTableUseCaseInput,
    GetTableUseCaseInput,
    ListTablesUseCaseInput,
    ListTablesUseCaseOutput,
    RenameTableUseCaseInput,
    UpdateTablePropertiesUseCaseInput,
)
from context.catalog.application.port.outbound.table import (
    PartitionSpec,
    Schema,
    SchemaField,
    Snapshot,
    SortOrder,
    Table,
    TableId,
)
from context.catalog.application.service.table import (
    CreateTableService,
    DeleteTableService,
    GetTableService,
    ListTablesService,
    RenameTableService,
    UpdateTablePropertiesService,
    table_id_from_parts,
)

if TYPE_CHECKING:
    from tests.context.catalog.fakes.in_memory_tables_repo import InMemoryTablesRepo

FIELDS = (
    CreateTableUseCaseInput.SchemaField(name="order_id", type="long", required=True, doc="key"),
    CreateTableUseCaseInput.SchemaField(name="order_ts", type="timestamptz", required=False),
)


def _create(
    repo: InMemoryTablesRepo,
    name: str = "orders",
    fields: tuple[CreateTableUseCaseInput.SchemaField, ...] | None = None,
    partition_fields: tuple[CreateTableUseCaseInput.PartitionField, ...] | None = None,
):
    return CreateTableService(repo).execute(
        CreateTableUseCaseInput(
            catalog="sales",
            namespace=("retail",),
            name=name,
            schema_fields=FIELDS if fields is None else fields,
            partition_fields=partition_fields or (),
            location=None,
            properties={"owner": "data-eng"},
        )
    )


def _with_snapshots(repo: InMemoryTablesRepo) -> None:
    """Store a loaded table with two snapshots, the second current."""
    table_id = TableId.of("sales", ("retail",), "orders")
    repo.items[table_id.value] = Table(
        id=table_id,
        uuid="u-1",
        format_version=2,
        location="s3://w/retail/orders",
        current_snapshot_id=2,
        last_updated_ms=20,
        schemas=(
            Schema(schema_id=0, fields=(SchemaField(id=1, name="order_id", type="long", required=True, doc=None),)),
        ),
        current_schema_id=0,
        partition_specs=(PartitionSpec.unpartitioned(),),
        default_spec_id=0,
        sort_order=SortOrder.unsorted(),
        snapshots=[
            Snapshot(
                snapshot_id=1, parent_id=None, timestamp_ms=10, operation="append", summary={"total-records": "5"}
            ),
            Snapshot(
                snapshot_id=2,
                parent_id=1,
                timestamp_ms=20,
                schema_id=0,
                operation="append",
                summary={"total-records": "9", "total-data-files": "3", "total-files-size": "300"},
            ),
        ],
        properties={},
    )


def test_create_table_assigns_field_ids_and_builds_the_partition_spec(tables_repo: InMemoryTablesRepo):
    """Fields get ids 1..n in form order; each partition field points at its source column by id."""
    output = _create(
        tables_repo,
        partition_fields=(
            CreateTableUseCaseInput.PartitionField(source_column="order_ts", transform="day"),
            CreateTableUseCaseInput.PartitionField(source_column="order_id", transform="bucket[16]"),
            CreateTableUseCaseInput.PartitionField(source_column="order_id", transform="identity"),
        ),
    )

    assert output.table_schema["fields"] == [
        {"id": 1, "name": "order_id", "type": "long", "required": True, "doc": "key"},
        {"id": 2, "name": "order_ts", "type": "timestamptz", "required": False, "doc": None},
    ]
    assert output.partition_spec == {
        "spec_id": 0,
        "fields": [
            {"source_id": 2, "field_id": 1000, "name": "order_ts_day", "transform": "day"},
            {"source_id": 1, "field_id": 1001, "name": "order_id_bucket", "transform": "bucket[16]"},
            {"source_id": 1, "field_id": 1002, "name": "order_id", "transform": "identity"},
        ],
    }
    assert (output.uuid, output.properties) == ("uuid-1", {"owner": "data-eng"})


def test_create_table_needs_a_field(tables_repo: InMemoryTablesRepo):
    """A table without schema fields is refused."""
    with pytest.raises(ValidationError, match="at least one field"):
        _create(tables_repo, fields=())


def test_create_table_refuses_duplicate_or_blank_field_names(tables_repo: InMemoryTablesRepo):
    """Field names are unique and not blank, and a field has a type."""
    with pytest.raises(ValidationError, match="duplicate"):
        _create(tables_repo, fields=(FIELDS[0], FIELDS[0]))
    with pytest.raises(ValidationError, match="blank"):
        _create(tables_repo, fields=(CreateTableUseCaseInput.SchemaField(name=" ", type="long"),))
    with pytest.raises(ValidationError, match="type"):
        _create(tables_repo, fields=(CreateTableUseCaseInput.SchemaField(name="a", type=" "),))


def test_create_table_refuses_an_unknown_partition_source(tables_repo: InMemoryTablesRepo):
    """A partition field must name a schema field."""
    with pytest.raises(ValidationError, match="nope"):
        _create(
            tables_repo,
            partition_fields=(CreateTableUseCaseInput.PartitionField(source_column="nope", transform="identity"),),
        )


@pytest.mark.parametrize("transform", ["bucket", "bucket[0]", "truncate[x]", "weekly", ""])
def test_create_table_refuses_an_unknown_transform(tables_repo: InMemoryTablesRepo, transform: str):
    """Only the Iceberg partition transforms are allowed."""
    with pytest.raises(ValidationError, match="transform"):
        _create(
            tables_repo,
            partition_fields=(CreateTableUseCaseInput.PartitionField(source_column="order_id", transform=transform),),
        )


def test_create_existing_table_is_a_conflict(tables_repo: InMemoryTablesRepo):
    """Creating a taken name passes the catalog's conflict through."""
    _create(tables_repo)

    with pytest.raises(ConflictError):
        _create(tables_repo)


def test_get_table_maps_snapshots_and_summary_of_the_current_snapshot(tables_repo: InMemoryTablesRepo):
    """Get returns primitives only: snapshots as dicts and the counts of the current snapshot."""
    _with_snapshots(tables_repo)

    output = GetTableService(tables_repo).execute(
        GetTableUseCaseInput(catalog="sales", namespace=("retail",), name="orders")
    )

    assert (output.catalog, output.namespace, output.name, output.uuid) == ("sales", ("retail",), "orders", "u-1")
    assert output.current_snapshot_id == 2
    assert output.snapshots[1] == {
        "id": 2,
        "parent_id": 1,
        "timestamp_ms": 20,
        "schema_id": 0,
        "operation": "append",
        "summary": {"total-records": "9", "total-data-files": "3", "total-files-size": "300"},
    }
    assert output.summary == {"total_records": 9, "total_data_files": 3, "total_files_size": 300}
    assert output.sort_order == {"order_id": 0, "fields": []}
    assert output.table_schema == {
        "schema_id": 0,
        "fields": [{"id": 1, "name": "order_id", "type": "long", "required": True, "doc": None}],
    }


def test_get_unknown_table_is_not_found(tables_repo: InMemoryTablesRepo):
    """A missing table raises NotFoundError naming it."""
    with pytest.raises(NotFoundError, match="orders"):
        GetTableService(tables_repo).execute(
            GetTableUseCaseInput(catalog="sales", namespace=("retail",), name="orders")
        )


def test_list_tables_returns_the_tables_of_the_namespace(tables_repo: InMemoryTablesRepo):
    """Listing returns the ids of the namespace's tables, not those of other namespaces."""
    _create(tables_repo, name="orders")
    _create(tables_repo, name="items")
    CreateTableService(tables_repo).execute(
        CreateTableUseCaseInput(catalog="sales", namespace=("other",), name="x", schema_fields=FIELDS)
    )

    output = ListTablesService(tables_repo).execute(ListTablesUseCaseInput(catalog="sales", namespace=("retail",)))

    assert output.items == (
        ListTablesUseCaseOutput.Table(catalog="sales", namespace=("retail",), name="items"),
        ListTablesUseCaseOutput.Table(catalog="sales", namespace=("retail",), name="orders"),
    )


def test_delete_table_removes_it(tables_repo: InMemoryTablesRepo):
    """Delete drops the table; a second delete is not found."""
    _create(tables_repo)
    service = DeleteTableService(tables_repo)

    service.execute(DeleteTableUseCaseInput(catalog="sales", namespace=("retail",), name="orders"))

    assert tables_repo.items == {}
    with pytest.raises(NotFoundError):
        service.execute(DeleteTableUseCaseInput(catalog="sales", namespace=("retail",), name="orders"))


def test_rename_table_moves_it_to_the_target(tables_repo: InMemoryTablesRepo):
    """Rename moves the table across namespaces and returns the new identity."""
    _create(tables_repo)

    output = RenameTableService(tables_repo).execute(
        RenameTableUseCaseInput(
            catalog="sales",
            namespace=("retail",),
            name="orders",
            target_namespace=("archive",),
            target_name="orders_old",
        )
    )

    assert (output.catalog, output.namespace, output.name) == ("sales", ("archive",), "orders_old")
    assert list(tables_repo.items) == [TableId.of("sales", ("archive",), "orders_old").value]


def test_rename_table_validates_the_target(tables_repo: InMemoryTablesRepo):
    """A blank target name is refused."""
    _create(tables_repo)

    with pytest.raises(ValidationError):
        RenameTableService(tables_repo).execute(
            RenameTableUseCaseInput(
                catalog="sales", namespace=("retail",), name="orders", target_namespace=("retail",), target_name=" "
            )
        )


def test_update_properties_applies_the_change(tables_repo: InMemoryTablesRepo):
    """Update sets and removes properties of the table that was loaded."""
    created = _create(tables_repo)

    output = UpdateTablePropertiesService(tables_repo).execute(
        UpdateTablePropertiesUseCaseInput(
            catalog="sales",
            namespace=("retail",),
            name="orders",
            expected_uuid=created.uuid,
            updates={"tier": "gold"},
            removals=("owner",),
        )
    )

    assert output.properties == {"tier": "gold"}
    assert output.table_schema["fields"][0]["name"] == "order_id"


def test_update_properties_conflict_on_replaced_table(tables_repo: InMemoryTablesRepo):
    """A table dropped and created again under the same name is another table: the save is refused."""
    loaded = _create(tables_repo)
    DeleteTableService(tables_repo).execute(
        DeleteTableUseCaseInput(catalog="sales", namespace=("retail",), name="orders")
    )
    _create(tables_repo)

    with pytest.raises(ConflictError) as raised:
        UpdateTablePropertiesService(tables_repo).execute(
            UpdateTablePropertiesUseCaseInput(
                catalog="sales",
                namespace=("retail",),
                name="orders",
                expected_uuid=loaded.uuid,
                updates={"tier": "gold"},
            )
        )
    assert str(raised.value) == "table orders changed since you loaded it, reload"


def test_update_properties_refuses_a_key_both_set_and_removed(tables_repo: InMemoryTablesRepo):
    """A key cannot be set and removed in one change."""
    created = _create(tables_repo)

    with pytest.raises(ValidationError, match="tier"):
        UpdateTablePropertiesService(tables_repo).execute(
            UpdateTablePropertiesUseCaseInput(
                catalog="sales",
                namespace=("retail",),
                name="orders",
                expected_uuid=created.uuid,
                updates={"tier": "g"},
                removals=("tier",),
            )
        )


def test_update_properties_needs_the_loaded_uuid(tables_repo: InMemoryTablesRepo):
    """Without the uuid that was loaded there is nothing to guard the save with."""
    _create(tables_repo)

    with pytest.raises(ValidationError, match="expected_uuid"):
        UpdateTablePropertiesService(tables_repo).execute(
            UpdateTablePropertiesUseCaseInput(catalog="sales", namespace=("retail",), name="orders", expected_uuid=" ")
        )


@pytest.mark.parametrize(("namespace", "name"), [((), "t"), (("a",), ""), (("a",), "x\x1fy"), ((" ",), "t")])
def test_table_id_from_parts_rejects_bad_parts(namespace: tuple[str, ...], name: str):
    """A table needs a namespace, a name without U+001F, and no blank part."""
    with pytest.raises(ValidationError):
        table_id_from_parts("sales", namespace, name)


@pytest.mark.parametrize(
    ("catalog", "namespace", "name"),
    [("a\x1fb", ("c",), "t"), ("sales", ("a\x1fb",), "t"), ("sales", ("a",), "t\x1fu")],
)
def test_table_id_from_parts_refuses_the_unit_separator_anywhere(catalog: str, namespace: tuple[str, ...], name: str):
    """U+001F in the catalog, a part or the name is a validation error, never another table's id."""
    with pytest.raises(ValidationError, match="must not contain the unit separator U\\+001F"):
        table_id_from_parts(catalog, namespace, name)


def test_get_unknown_table_names_the_namespace_as_a_list(tables_repo: InMemoryTablesRepo):
    """The 404 text prints the namespace parts as a list, as the REST detail always did."""
    with pytest.raises(NotFoundError) as raised:
        GetTableService(tables_repo).execute(
            GetTableUseCaseInput(catalog="sales", namespace=("a", "b.c"), name="orders")
        )
    assert str(raised.value) == "table orders not found in namespace ['a', 'b.c'] of catalog sales"
