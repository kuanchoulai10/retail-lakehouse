"""Define the table_schema_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.table.polaris.iceberg_type_from_polaris import (
    iceberg_type_from_polaris,
)
from context.catalog.application.port.outbound.table import SchemaField, TableSchema

if TYPE_CHECKING:
    from collections.abc import Mapping


def table_schema_from_polaris(metadata: Mapping[str, Any]) -> TableSchema:
    """Map the current schema of Iceberg table metadata: ``schemas`` at ``current-schema-id``, else v1 ``schema``."""
    current_id = metadata.get("current-schema-id")
    schema = next(
        (s for s in metadata.get("schemas") or [] if s.get("schema-id") == current_id),
        metadata.get("schema") or {},
    )
    return TableSchema(
        schema_id=int(schema.get("schema-id", 0)),
        fields=tuple(
            SchemaField(
                id=int(field["id"]),
                name=str(field["name"]),
                type=iceberg_type_from_polaris(field["type"]),
                required=bool(field.get("required")),
                doc=field.get("doc"),
            )
            for field in schema.get("fields", [])
        ),
    )
