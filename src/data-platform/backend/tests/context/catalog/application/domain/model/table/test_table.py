"""Test the TableId identifier, the Table aggregate and its summary."""

from __future__ import annotations

import pytest

from context.catalog.application.domain.model.shared import Schema, SchemaField
from context.catalog.application.domain.model.table import (
    PartitionSpec,
    Snapshot,
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
        schema=Schema(schema_id=0, fields=(SchemaField(1, "id", "long", True, None),)),
        partition_spec=PartitionSpec.unpartitioned(),
        location=None,
        properties={},
    )

    assert (table.uuid, table.format_version, table.current_snapshot_id, table.snapshots) == (None, None, None, [])
    assert table.sort_order == SortOrder.unsorted()
    assert table.summary == TableSummary(total_records=None, total_data_files=None, total_files_size=None)


def test_summary_reads_the_current_snapshot_only():
    """The counts come from the current snapshot's summary; a missing or non-numeric key is None."""
    current = Snapshot(2, 1, 20, "append", {"total-records": "9", "total-files-size": "n/a"})
    older = Snapshot(1, None, 10, "append", {"total-records": "5", "total-data-files": "1"})

    assert TableSummary.of(current) == TableSummary(total_records=9, total_data_files=None, total_files_size=None)
    assert TableSummary.of(older).total_data_files == 1
    assert TableSummary.of(None) == TableSummary(None, None, None)


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
