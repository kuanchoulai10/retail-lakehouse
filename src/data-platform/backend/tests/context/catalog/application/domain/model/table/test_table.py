"""Test the TableId identifier, the Table aggregate and its summary."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from context.catalog.application.domain.model.shared import Schema, SchemaField
from context.catalog.application.domain.model.table import (
    NullOrder,
    PartitionField,
    PartitionSpec,
    Snapshot,
    SortDirection,
    SortField,
    SortOrder,
    Table,
    TableId,
    TableSummary,
)


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
    with pytest.raises(ValidationError):
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
        ("current_schema", "schema 0"),
        ("partition_spec", "unpartitioned"),
        ("sort_order", ("asc",)),
        ("snapshots", ({"snapshot_id": 1},)),
        ("properties", {"a": 1}),
    ],
)
def test_assigning_a_wrong_type_is_rejected_and_changes_nothing(field: str, value: object):
    """Every assignment is validated strictly; a rejected one leaves the table as it was."""
    table = _orders()
    before = table.model_dump()

    with pytest.raises(ValidationError):
        setattr(table, field, value)

    assert table.model_dump() == before


@pytest.mark.parametrize(
    ("value", "field", "change"),
    [
        (PartitionField(source_id=1, field_id=1000, name="id", transform="identity"), "name", "other"),
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
    with pytest.raises(ValidationError):
        setattr(value, field, change)


def test_table_value_objects_are_strict():
    """A plain string is not a sort direction, a list is not a tuple and a bool is not an id."""
    with pytest.raises(ValidationError):
        SortField(source_id=1, transform="identity", direction="asc", null_order=NullOrder.NULLS_FIRST)  # ty: ignore[invalid-argument-type]
    with pytest.raises(ValidationError):
        PartitionSpec(spec_id=0, fields=[])  # ty: ignore[invalid-argument-type]
    with pytest.raises(ValidationError):
        PartitionField(source_id=True, field_id=1000, name="id", transform="identity")
    with pytest.raises(ValidationError):
        Snapshot(snapshot_id=1, parent_id=None, timestamp_ms=10, operation="append", summary={"k": 1})  # ty: ignore[invalid-argument-type]


def test_table_value_objects_require_keywords():
    """Value objects are built by field name; positional values are refused."""
    with pytest.raises(TypeError):
        PartitionSpec(0, ())  # ty: ignore[too-many-positional-arguments, missing-argument]
