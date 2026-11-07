"""Define the namespace_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.shared.polaris import namespace_parts_from_polaris, read_polaris_reply
from context.catalog.application.port.outbound.namespace import Namespace, NamespaceId

if TYPE_CHECKING:
    import httpx


def _namespace(catalog: str, body: dict[str, Any]) -> Namespace:
    properties = body.get("properties") or {}
    if not isinstance(properties, dict):
        raise TypeError(f"properties must be an object, not {properties!r}")
    return Namespace(
        id=NamespaceId.of(catalog, namespace_parts_from_polaris(body["namespace"])),
        properties={str(key): str(value) for key, value in properties.items()},
    )


def namespace_from_polaris(catalog: str, parts: tuple[str, ...], response: httpx.Response) -> Namespace:
    """Map an Iceberg REST namespace reply, ``{"namespace": [...], "properties": {...}}``, to a Namespace.

    ``parts`` names the namespace asked for. A reply that is not a JSON object, has no
    ``namespace`` list of strings, or has properties that are not an object raises
    CatalogUnavailableError naming that namespace, so the API answers 502 rather than 500.
    Properties may be left out; the namespace never is.
    """
    return read_polaris_reply(response, f"namespace {list(parts)}", lambda body: _namespace(catalog, body))
