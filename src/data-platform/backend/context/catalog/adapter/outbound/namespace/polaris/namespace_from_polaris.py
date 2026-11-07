"""Define the namespace_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.application.port.outbound.namespace import Namespace, NamespaceId

if TYPE_CHECKING:
    from collections.abc import Mapping


def namespace_from_polaris(catalog: str, body: Mapping[str, Any]) -> Namespace:
    """Map an Iceberg REST namespace body, ``{"namespace": [...], "properties": {...}}``, to a Namespace."""
    parts = tuple(str(part) for part in body.get("namespace") or ())
    properties = body.get("properties") or {}
    return Namespace(
        id=NamespaceId.of(catalog, parts),
        properties={str(key): str(value) for key, value in properties.items()},
    )
