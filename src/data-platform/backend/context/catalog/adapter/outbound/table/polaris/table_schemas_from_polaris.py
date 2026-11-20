"""Define the table_schemas_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.shared.polaris import iceberg_schema_from_polaris, polaris_integer

if TYPE_CHECKING:
    from collections.abc import Mapping

    from context.catalog.application.port.outbound.table import Schema


def table_schemas_from_polaris(metadata: Mapping[str, Any]) -> tuple[tuple[Schema, ...], int]:
    """Map every schema of Iceberg table metadata, sorted by id, with the id ``current-schema-id`` names.

    Only metadata without ``schemas`` (format v1) falls back to its single ``schema``, whose
    ``schema-id`` (0 when absent) is then the current id. A current id that matches no schema
    raises ValueError instead of yielding an empty schema; an id that is not an integer raises
    TypeError.
    """
    if "schemas" not in metadata:
        schema = iceberg_schema_from_polaris(metadata["schema"])
        return (schema,), schema.schema_id
    current_id = polaris_integer(metadata["current-schema-id"], "current-schema-id")
    schemas = tuple(
        sorted(
            (iceberg_schema_from_polaris(schema) for schema in metadata["schemas"]), key=lambda schema: schema.schema_id
        )
    )
    if current_id not in {schema.schema_id for schema in schemas}:
        raise ValueError(f"current-schema-id {current_id} matches no schema")
    return schemas, current_id
