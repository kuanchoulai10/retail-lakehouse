"""Define the view_to_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.shared.polaris import iceberg_schema_to_polaris

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.view import View

_SUMMARY_ENGINE_VERSION = "1.0.0"


def view_to_polaris(view: View) -> dict[str, Any]:
    """Map a view defined for create to an Iceberg REST CreateViewRequest.

    The body holds the name, the schema, the current version as ``view-version`` with one sql
    representation, and the properties; ``location`` is left out unless the view has one, so
    Polaris picks it. The version summary names the dialect as the engine, as the upstream
    console does.
    """
    version = view.current_version
    body: dict[str, Any] = {"name": view.id.name}
    if view.location:
        body["location"] = view.location
    body["schema"] = iceberg_schema_to_polaris(view.schema)
    body["view-version"] = {
        "version-id": version.version_id,
        "timestamp-ms": version.timestamp_ms,
        "schema-id": version.schema_id,
        "summary": {"engine-name": version.dialect, "engine-version": _SUMMARY_ENGINE_VERSION},
        "representations": [{"type": "sql", "sql": version.query, "dialect": version.dialect}],
        "default-namespace": list(version.default_namespace),
    }
    body["properties"] = dict(view.properties)
    return body
