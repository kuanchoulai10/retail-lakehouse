"""Define the table_property_output_fields function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.application.domain.model.table import iceberg_table_property_catalogue
from context.catalog.application.domain.service.table import resolve_table_properties

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.catalog import Catalog
    from context.catalog.application.port.outbound.table import Table


def table_property_output_fields(table: Table, catalog: Catalog) -> dict[str, Any]:
    """Return the primitive fields shared by the ListTableProperties and ResetTableProperties outputs.

    ``items`` holds one primitive dict per resolved property, ordered by key.
    """
    catalogue = iceberg_table_property_catalogue()
    return {
        "uuid": table.uuid,
        "iceberg_version": catalogue.iceberg_version,
        "items": [
            {
                "key": row.key,
                "current_value": row.current_value,
                "default_value": row.default_value,
                "default_source": None if row.default_source is None else str(row.default_source),
                "modified": row.modified,
                "custom": row.custom,
                "resettable": row.resettable,
                "description": row.description,
            }
            for row in resolve_table_properties(table, catalog, catalogue)
        ],
    }
