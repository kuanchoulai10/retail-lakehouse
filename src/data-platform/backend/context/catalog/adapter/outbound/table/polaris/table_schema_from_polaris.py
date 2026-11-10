"""Define the table_schema_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.shared.polaris import iceberg_schema_from_polaris, polaris_integer

if TYPE_CHECKING:
    from collections.abc import Mapping

    from context.catalog.application.port.outbound.table import Schema


def _current(metadata: Mapping[str, Any]) -> Mapping[str, Any]:
    if "schemas" not in metadata:
        return metadata["schema"]
    current_id = polaris_integer(metadata["current-schema-id"], "current-schema-id")
    for schema in metadata["schemas"]:
        if polaris_integer(schema["schema-id"], "schema-id") == current_id:
            return schema
    raise ValueError(f"current-schema-id {current_id} matches no schema")


def table_schema_from_polaris(metadata: Mapping[str, Any]) -> Schema:
    """Map the current schema of Iceberg table metadata: ``schemas`` at ``current-schema-id``.

    Only metadata without ``schemas`` (format v1) falls back to its single ``schema``. A
    current id that matches no schema raises ValueError instead of yielding an empty schema;
    an id that is not an integer raises TypeError.
    """
    return iceberg_schema_from_polaris(_current(metadata))
