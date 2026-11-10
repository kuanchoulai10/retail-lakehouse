"""Define the view_version_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.shared.polaris import polaris_integer, polaris_text
from context.catalog.application.port.outbound.view import ViewVersion

if TYPE_CHECKING:
    from collections.abc import Mapping

_SQL = "sql"


def _sql_representation(version: Mapping[str, Any]) -> Mapping[str, Any]:
    for representation in version["representations"]:
        if representation["type"] == _SQL:
            return representation
    raise ValueError(f"version {version['version-id']} has no sql representation")


def view_version_from_polaris(version: Mapping[str, Any]) -> ViewVersion:
    """Map one ``versions`` entry of view metadata to a ViewVersion.

    The version's sql and dialect come from its first ``sql`` representation. A version with
    none, whose sql, dialect or default namespace is not text, or whose id, timestamp or schema
    id is not an integer (a bool is not one), raises instead of yielding an empty sql or a
    coerced number.
    """
    representation = _sql_representation(version)
    namespace = version["default-namespace"]
    if not isinstance(namespace, list):
        raise TypeError(f"default-namespace must be a list, not {namespace!r}")
    return ViewVersion(
        version_id=polaris_integer(version["version-id"], "version-id"),
        timestamp_ms=polaris_integer(version["timestamp-ms"], "timestamp-ms"),
        schema_id=polaris_integer(version["schema-id"], "schema-id"),
        query=polaris_text(representation["sql"], "sql"),
        dialect=polaris_text(representation["dialect"], "dialect"),
        default_namespace=tuple(polaris_text(part, "default-namespace part") for part in namespace),
    )
