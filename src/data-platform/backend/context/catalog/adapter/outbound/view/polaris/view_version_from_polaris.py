"""Define the view_version_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.application.port.outbound.view import ViewVersion

if TYPE_CHECKING:
    from collections.abc import Mapping

_SQL = "sql"


def _text(value: object, what: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{what} must be text, not {value!r}")
    return value


def _sql_representation(version: Mapping[str, Any]) -> Mapping[str, Any]:
    for representation in version["representations"]:
        if representation["type"] == _SQL:
            return representation
    raise ValueError(f"version {version['version-id']} has no sql representation")


def view_version_from_polaris(version: Mapping[str, Any]) -> ViewVersion:
    """Map one ``versions`` entry of view metadata to a ViewVersion.

    The version's sql and dialect come from its first ``sql`` representation. A version with
    none, or whose sql, dialect or default namespace is not text, raises instead of yielding
    an empty sql.
    """
    representation = _sql_representation(version)
    namespace = version["default-namespace"]
    if not isinstance(namespace, list):
        raise TypeError(f"default-namespace must be a list, not {namespace!r}")
    return ViewVersion(
        version_id=int(version["version-id"]),
        timestamp_ms=int(version["timestamp-ms"]),
        schema_id=int(version["schema-id"]),
        query=_text(representation["sql"], "sql"),
        dialect=_text(representation["dialect"], "dialect"),
        default_namespace=tuple(_text(part, "default-namespace part") for part in namespace),
    )
