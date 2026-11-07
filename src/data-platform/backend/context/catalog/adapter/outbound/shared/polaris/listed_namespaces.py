"""Define the listed_namespaces function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.shared.polaris.namespace_parts_from_polaris import (
    namespace_parts_from_polaris,
)
from context.catalog.adapter.outbound.shared.polaris.raise_for_paged_listing import (
    raise_for_paged_listing,
)
from context.catalog.adapter.outbound.shared.polaris.read_polaris_reply import read_polaris_reply

if TYPE_CHECKING:
    import httpx


def _namespaces(body: dict[str, Any]) -> tuple[dict[str, Any], list[tuple[str, ...]]]:
    listed = body["namespaces"]
    if not isinstance(listed, list):
        raise TypeError(f"namespaces must be a list, not {listed!r}")
    return body, [namespace_parts_from_polaris(parts) for parts in listed]


def listed_namespaces(response: httpx.Response, catalog: str) -> list[tuple[str, ...]]:
    """Return the parts of each namespace of an Iceberg REST ListNamespacesResponse from ``catalog``.

    A reply without a ``namespaces`` list of string lists raises CatalogUnavailableError; a
    paged listing raises it too (Ruling R8), so nothing is cut short.
    """
    body, found = read_polaris_reply(response, f"the namespaces of catalog {catalog}", _namespaces)
    raise_for_paged_listing(body)
    return found
