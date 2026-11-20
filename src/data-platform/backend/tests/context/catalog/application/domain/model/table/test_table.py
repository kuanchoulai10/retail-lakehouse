"""Test the TableId identifier, the Table aggregate and its summary."""

from __future__ import annotations

import pytest

from base import InvariantViolation
from context.catalog.application.domain.model.shared import Schema, SchemaField, SchemaFieldKind
from context.catalog.application.domain.model.table import (
    NullOrder,
    PartitionField,
    PartitionSpec,
    PartitionTransform,
    PartitionTransformKind,
    Snapshot,
    SortDirection,
    SortField,
    SortOrder,
    Table,
    TableId,
    TableSummary,
)

IDENTITY = PartitionTransform(kind=PartitionTransformKind.IDENTITY)


def test_table_id_joins_catalog_namespace_and_name_with_the_unit_separator():
    """The value is the catalog, the namespace parts and the name, joined by U+001F."""
    table_id = TableId.of("sales", ("a", "b.c"), "orders")

    assert table_id.value == "sales\x1fa\x1fb.c\x1forders"
    assert (table_id.catalog, table_id.namespace, table_id.name) == ("sales", ("a", "b.c"), "orders")


def test_defined_table_has_no_catalog_assigned_facts_yet():
    """A table defined for create has no uuid, format version or snapshots until the catalog saves it."""
    table = Table.define(
        id=TableId.of("sales", ("retail",), "orders"),
        schema=Schema(schema_id=0, fields=(SchemaField(id=1, name="id", type="long", required=True, doc=None),)),
        partition_spec=PartitionSpec.unpartitioned(),
        location=None,
        properties={},
    )

    assert (table.uuid, table.format_version, table.current_snapshot_id, table.snapshots) == (None, None, None, [])
    assert table.sort_order == SortOrder.unsorted()
    assert table.summary == TableSummary(total_records=None, total_data_files=None, total_files_size=None)


def test_summary_reads_the_current_snapshot_only():
    """The counts come from the current snapshot's summary; a missing or non-numeric key is None."""
    current = Snapshot(
        snapshot_id=2,
        parent_id=1,
        timestamp_ms=20,
        operation="append",
        summary={"total-records": "9", "total-files-size": "n/a"},
    )
    older = Snapshot(
        snapshot_id=1,
        parent_id=None,
        timestamp_ms=10,
        operation="append",
        summary={"total-records": "5", "total-data-files": "1"},
    )

    assert TableSummary.of(current) == TableSummary(total_records=9, total_data_files=None, total_files_size=None)
    assert TableSummary.of(older).total_data_files == 1
    assert TableSummary.of(None) == TableSummary(total_records=None, total_data_files=None, total_files_size=None)


@pytest.mark.parametrize(
    ("catalog", "namespace", "name", "message"),
    [
        ("a\x1fb", ("c",), "t", "catalog name must not contain"),
        ("sales", ("a\x1fb",), "t", "namespace parts must not contain"),
        ("sales", ("a",), "t\x1fu", "table name must not contain"),
    ],
)
def test_table_id_refuses_the_unit_separator_inside_any_component(catalog, namespace, name, message):
    """A U+001F inside the catalog, a namespace part or the name would split differently, so it is refused."""
    with pytest.raises(ValueError, match=message):
        TableId.of(catalog, namespace, name)


def _orders() -> Table:
    return Table.define(
        id=TableId.of("sales", ("retail",), "orders"),
        schema=Schema(schema_id=0, fields=(SchemaField(id=1, name="id", type="long", required=True, doc=None),)),
        partition_spec=PartitionSpec.unpartitioned(),
        location=None,
        properties={"owner": "data-eng"},
    )


def test_table_id_is_built_positionally_and_strict():
    """The id keeps its positional form and takes only a string."""
    assert TableId("sales\x1fretail\x1forders") == TableId.of("sales", ("retail",), "orders")
    with pytest.raises(InvariantViolation):
        TableId(1)  # ty: ignore[invalid-argument-type]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("uuid", 1),
        ("format_version", "2"),
        ("format_version", True),
        ("location", 3),
        ("current_snapshot_id", "1"),
        ("last_updated_ms", 1.5),
        ("schemas", ("schema 0",)),
        ("current_schema_id", "0"),
        ("partition_specs", ("unpartitioned",)),
        ("default_spec_id", "0"),
        ("sort_order", ("asc",)),
        ("snapshots", ({"snapshot_id": 1},)),
        ("properties", {"a": 1}),
    ],
)
def test_assigning_a_wrong_type_is_rejected_and_changes_nothing(field: str, value: object):
    """Every assignment is validated strictly; a rejected one leaves the table as it was."""
    table = _orders()
    before = table.model_dump()

    with pytest.raises(InvariantViolation):
        setattr(table, field, value)

    assert table.model_dump() == before


@pytest.mark.parametrize(
    ("value", "field", "change"),
    [
        (PartitionField(source_id=1, field_id=1000, name="id", transform=IDENTITY), "name", "other"),
        (PartitionSpec.unpartitioned(), "spec_id", 1),
        (Snapshot(snapshot_id=1, parent_id=None, timestamp_ms=10, operation="append", summary={}), "parent_id", 2),
        (
            SortField(source_id=1, transform="identity", direction=SortDirection.ASC, null_order=NullOrder.NULLS_FIRST),
            "direction",
            SortDirection.DESC,
        ),
        (SortOrder.unsorted(), "order_id", 1),
        (TableSummary(total_records=1, total_data_files=1, total_files_size=1), "total_records", 2),
    ],
)
def test_table_value_objects_are_immutable(value: object, field: str, change: object):
    """A value object of the table cannot change after it is built."""
    with pytest.raises(AttributeError, match="is immutable"):
        setattr(value, field, change)


def test_table_value_objects_are_strict():
    """A plain string is not a sort direction, a list is not a tuple and a bool is not an id."""
    with pytest.raises(InvariantViolation):
        SortField(source_id=1, transform="identity", direction="asc", null_order=NullOrder.NULLS_FIRST)  # ty: ignore[invalid-argument-type]
    with pytest.raises(InvariantViolation):
        PartitionSpec(spec_id=0, fields=[])  # ty: ignore[invalid-argument-type]
    with pytest.raises(InvariantViolation):
        PartitionField(source_id=True, field_id=1000, name="id", transform=IDENTITY)
    with pytest.raises(InvariantViolation):
        Snapshot(snapshot_id=1, parent_id=None, timestamp_ms=10, operation="append", summary={"k": 1})  # ty: ignore[invalid-argument-type]


def test_table_value_objects_require_keywords():
    """Value objects are built by field name; positional values are refused."""
    with pytest.raises(TypeError):
        PartitionSpec(0, ())  # ty: ignore[too-many-positional-arguments, missing-argument]


def _schema(schema_id: int, *fields: SchemaField) -> Schema:
    return Schema(
        schema_id=schema_id, fields=fields or (SchemaField(id=1, name="id", type="long", required=True, doc=None),)
    )


def _spec(spec_id: int) -> PartitionSpec:
    return PartitionSpec(spec_id=spec_id, fields=())


def _versioned(
    schemas: tuple[Schema, ...] | None = None,
    current_schema_id: int = 1,
    partition_specs: tuple[PartitionSpec, ...] | None = None,
    default_spec_id: int = 1,
) -> Table:
    return Table(
        id=TableId.of("sales", ("retail",), "orders"),
        uuid="u-1",
        format_version=2,
        location="s3://w/retail/orders",
        current_snapshot_id=None,
        last_updated_ms=1,
        schemas=schemas or (_schema(0), _schema(1)),
        current_schema_id=current_schema_id,
        partition_specs=partition_specs or (_spec(0), _spec(1)),
        default_spec_id=default_spec_id,
        sort_order=SortOrder.unsorted(),
    )


def test_define_holds_one_schema_and_one_spec():
    """A defined table has its one schema as the current one and its one spec as the default."""
    schema = _schema(0)
    spec = PartitionSpec(spec_id=0, fields=(PartitionField(source_id=1, field_id=1000, name="id", transform=IDENTITY),))

    table = Table.define(
        id=TableId.of("sales", ("retail",), "orders"), schema=schema, partition_spec=spec, location=None, properties={}
    )

    assert table.schemas == (schema,) and table.current_schema_id == 0 and table.current_schema == schema
    assert table.partition_specs == (spec,) and table.default_spec_id == 0 and table.default_partition_spec == spec


def test_duplicate_schema_ids_are_refused():
    """Two schemas with one id leave the id naming two schemas."""
    with pytest.raises(InvariantViolation, match="schema ids"):
        _versioned(schemas=(_schema(0), _schema(1), _schema(1)))


def test_duplicate_partition_spec_ids_are_refused():
    """Two specs with one id leave the id naming two specs."""
    with pytest.raises(InvariantViolation, match="partition spec ids"):
        _versioned(partition_specs=(_spec(0), _spec(1), _spec(1)))


def test_current_schema_id_must_name_a_schema():
    """A current id with no schema behind it is refused."""
    with pytest.raises(InvariantViolation, match="current_schema_id 5"):
        _versioned(current_schema_id=5)


def test_default_spec_id_must_name_a_partition_spec():
    """A default id with no spec behind it is refused."""
    with pytest.raises(InvariantViolation, match="default_spec_id 5"):
        _versioned(default_spec_id=5)


def test_schemas_out_of_id_order_are_refused():
    """Schemas are held in ascending id order, so the previous version is the one before it."""
    with pytest.raises(InvariantViolation, match="schema ids"):
        _versioned(schemas=(_schema(1), _schema(0)))


def test_partition_specs_out_of_id_order_are_refused():
    """Specs are held in ascending id order."""
    with pytest.raises(InvariantViolation, match="partition spec ids"):
        _versioned(partition_specs=(_spec(1), _spec(0)))


def test_previous_schema_is_the_next_lower_id():
    """The previous schema of an id is the one with the largest id below it; the first has none."""
    table = _versioned(schemas=(_schema(0), _schema(1), _schema(2)), current_schema_id=2)

    previous = table.previous_schema(2)
    assert previous is not None and previous.schema_id == 1
    assert table.previous_schema(0) is None
    assert table.schema_by_id(1) == _schema(1)
    assert table.schema_by_id(7) is None


def test_previous_schema_skips_ids_the_table_does_not_have():
    """Schema ids 0, 3 and 5: the previous of 5 is 3."""
    table = _versioned(schemas=(_schema(0), _schema(3), _schema(5)), current_schema_id=5)

    previous = table.previous_schema(5)
    assert previous is not None and previous.schema_id == 3


def test_previous_partition_spec_is_the_next_lower_id():
    """Specs follow the same rule as schemas."""
    table = _versioned(partition_specs=(_spec(0), _spec(1), _spec(2)), default_spec_id=2)

    previous = table.previous_partition_spec(2)
    assert previous is not None and previous.spec_id == 1
    assert table.previous_partition_spec(0) is None
    assert table.partition_spec_by_id(1) == _spec(1)
    assert table.partition_spec_by_id(7) is None


def test_reused_schema_id_stays_current():
    """Iceberg reuses an existing schema id, so the current schema may sit below the highest id."""
    table = _versioned(schemas=(_schema(0), _schema(1), _schema(2)), current_schema_id=1)

    assert table.current_schema.schema_id == 1


def test_column_paths_prefer_the_current_schema():
    """A field id takes its path from the current schema, then from the highest schema id holding it."""
    customer_id = SchemaField(id=2, name="customer_id", type="long", required=False, doc=None)
    customer = SchemaField(id=2, name="customer", type="long", required=False, doc=None)
    legacy = SchemaField(id=3, name="legacy", type="string", required=False, doc=None)
    city = SchemaField(id=6, name="city", type="string", required=False, doc=None)
    shipping = SchemaField(
        id=5,
        name="shipping",
        type="struct<city: string>",
        required=False,
        doc=None,
        kind=SchemaFieldKind.STRUCT,
        children=(city,),
    )
    table = _versioned(
        schemas=(_schema(0, customer_id, legacy), _schema(1, customer, shipping)),
        current_schema_id=1,
    )

    paths = table.column_paths()

    assert paths[2] == ("customer",)
    assert paths[3] == ("legacy",)
    assert paths[5] == ("shipping",)
    assert paths[6] == ("shipping", "city")


def test_column_paths_prefer_a_higher_schema_id_over_a_lower_one_when_the_current_lacks_the_field():
    """With the current schema holding neither, the newest schema holding the id names it."""
    old = SchemaField(id=3, name="old_name", type="string", required=False, doc=None)
    newer = SchemaField(id=3, name="newer_name", type="string", required=False, doc=None)
    table = _versioned(schemas=(_schema(0, old), _schema(1, newer), _schema(2)), current_schema_id=2)

    assert table.column_paths()[3] == ("newer_name",)
