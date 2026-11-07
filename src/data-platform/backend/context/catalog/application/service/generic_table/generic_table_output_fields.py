"""Define the generic_table_output_fields function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.generic_table import GenericTable


def generic_table_output_fields(table: GenericTable) -> dict[str, Any]:
    """Return the primitive fields shared by the Get and Create generic table outputs."""
    return {
        "catalog": table.id.catalog,
        "namespace": list(table.id.namespace),
        "name": table.id.name,
        "format": table.format,
        "base_location": table.base_location,
        "doc": table.doc,
        "properties": dict(table.properties),
    }
