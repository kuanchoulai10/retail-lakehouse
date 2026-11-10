"""Define the view_output_fields function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.view import View


def view_output_fields(view: View) -> dict[str, Any]:
    """Return the primitive fields shared by the Get and Create view outputs."""
    return {
        "catalog": view.id.catalog,
        "namespace": list(view.id.namespace),
        "name": view.id.name,
        "uuid": view.uuid,
        "location": view.location,
        "query": view.query,
        "dialect": view.dialect,
        "default_namespace": list(view.default_namespace),
        "current_version_id": view.current_version_id,
        "schema": {
            "schema_id": view.current_schema.schema_id,
            "fields": [
                {"id": f.id, "name": f.name, "type": f.type, "required": f.required, "doc": f.doc}
                for f in view.current_schema.fields
            ],
        },
        "versions": [
            {"version_id": v.version_id, "timestamp_ms": v.timestamp_ms, "query": v.query} for v in view.versions
        ],
        "properties": dict(view.properties),
    }
