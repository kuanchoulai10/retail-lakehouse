"""Define the iceberg_schema_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.shared.polaris.iceberg_type_from_polaris import (
    iceberg_type_from_polaris,
)
from context.catalog.application.port.outbound.shared import Schema, SchemaField

if TYPE_CHECKING:
    from collections.abc import Mapping


def iceberg_schema_from_polaris(schema: Mapping[str, Any]) -> Schema:
    """Map one Iceberg REST schema struct to a Schema: its id and its top-level fields in order.

    A missing ``schema-id`` is 0. Types are rendered as text by ``iceberg_type_from_polaris``.
    """
    return Schema(
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
