"""Define the table_schema_to_polaris function."""

from __future__ import annotations

from itertools import count
from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.table.polaris.iceberg_type_to_polaris import (
    iceberg_type_to_polaris,
)

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.table import TableSchema


def table_schema_to_polaris(schema: TableSchema) -> dict[str, Any]:
    """Map a schema to an Iceberg REST struct; nested ids continue after the highest top-level id."""
    next_id = count(max((field.id for field in schema.fields), default=0) + 1).__next__
    fields = []
    for field in schema.fields:
        body: dict[str, Any] = {
            "id": field.id,
            "name": field.name,
            "type": iceberg_type_to_polaris(field.type, next_id),
            "required": field.required,
        }
        if field.doc:
            body["doc"] = field.doc
        fields.append(body)
    return {"type": "struct", "schema-id": schema.schema_id, "fields": fields}
