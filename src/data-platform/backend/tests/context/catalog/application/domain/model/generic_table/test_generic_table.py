"""Test the GenericTableId identifier and the GenericTable aggregate."""

from __future__ import annotations

from context.catalog.application.domain.model.generic_table import GenericTable, GenericTableId


def test_generic_table_id_joins_catalog_namespace_and_name_with_the_unit_separator():
    """The value is the catalog, the namespace parts and the name, joined by U+001F."""
    table_id = GenericTableId.of("sales", ("a", "b.c"), "events")

    assert table_id.value == "sales\x1fa\x1fb.c\x1fevents"
    assert (table_id.catalog, table_id.namespace, table_id.name) == ("sales", ("a", "b.c"), "events")


def test_generic_table_keeps_what_it_was_defined_with():
    """A generic table is its format, base location, doc and properties; it has no schema or uuid."""
    table = GenericTable(
        id=GenericTableId.of("sales", ("retail",), "events"),
        format="delta",
        base_location="s3://w/events",
        doc="clicks",
        properties={"owner": "data-eng"},
    )

    assert (table.format, table.base_location, table.doc, table.properties) == (
        "delta",
        "s3://w/events",
        "clicks",
        {"owner": "data-eng"},
    )
