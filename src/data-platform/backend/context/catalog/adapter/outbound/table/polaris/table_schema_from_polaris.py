"""Define the table_schema_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.table.polaris.iceberg_type_from_polaris import (
    iceberg_type_from_polaris,
)
from context.catalog.application.port.outbound.table import SchemaField, TableSchema

if TYPE_CHECKING:
    from collections.abc import Mapping


def _current(metadata: Mapping[str, Any]) -> Mapping[str, Any]:
    if "schemas" not in metadata:
        return metadata["schema"]
    current_id = metadata["current-schema-id"]
    for schema in metadata["schemas"]:
        if schema["schema-id"] == current_id:
            return schema
    raise ValueError(f"current-schema-id {current_id} matches no schema")


def table_schema_from_polaris(metadata: Mapping[str, Any]) -> TableSchema:
    """Map the current schema of Iceberg table metadata: ``schemas`` at ``current-schema-id``.

    Only metadata without ``schemas`` (format v1) falls back to its single ``schema``. A
    current id that matches no schema raises ValueError instead of yielding an empty schema.
    """
    schema = _current(metadata)
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
            for field in schema["fields"]
        ),
    )
