"""Define the view_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.shared.polaris import (
    iceberg_schema_from_polaris,
    polaris_integer,
    polaris_text,
    polaris_text_map,
    read_polaris_reply,
)
from context.catalog.adapter.outbound.view.polaris.view_version_from_polaris import (
    view_version_from_polaris,
)
from context.catalog.application.port.outbound.view import View

if TYPE_CHECKING:
    from collections.abc import Mapping

    import httpx

    from context.catalog.application.port.outbound.view import Schema, ViewId, ViewVersion


def _current_version(versions: list[ViewVersion], current_id: int) -> ViewVersion:
    for version in versions:
        if version.version_id == current_id:
            return version
    raise ValueError(f"current-version-id {current_id} matches no version")


def _schema_of(metadata: Mapping[str, Any], version: ViewVersion) -> Schema:
    for schema in metadata["schemas"]:
        if schema["schema-id"] == version.schema_id:
            return iceberg_schema_from_polaris(schema)
    raise ValueError(f"schema-id {version.schema_id} of the current version matches no schema")


def _view(view_id: ViewId, metadata: Mapping[str, Any]) -> View:
    versions = [view_version_from_polaris(version) for version in metadata["versions"]]
    current = _current_version(versions, polaris_integer(metadata["current-version-id"], "current-version-id"))
    return View(
        id=view_id,
        uuid=polaris_text(metadata["view-uuid"], "view-uuid"),
        location=polaris_text(metadata["location"], "location"),
        current_schema=_schema_of(metadata, current),
        current_version_id=current.version_id,
        versions=versions,
        properties=polaris_text_map(metadata.get("properties"), "properties"),
    )


def view_from_polaris(view_id: ViewId, response: httpx.Response) -> View:
    """Map the ``metadata`` of a LoadViewResult reply to a View.

    The current version is the one ``current-version-id`` names and the schema is the one that
    version's ``schema-id`` names. An id that matches nothing, a version with no sql, or
    metadata this backend cannot read raises CatalogUnavailableError naming the view, so the
    API answers 502 rather than 500 or an empty view. The ``config`` block, which may carry
    storage credentials, is never read.
    """
    return read_polaris_reply(response, f"view {view_id.name}", lambda body: _view(view_id, body["metadata"]))
