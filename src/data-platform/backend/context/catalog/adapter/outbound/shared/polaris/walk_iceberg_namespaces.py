"""Define the walk_iceberg_namespaces function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.adapter.outbound.shared.polaris.iceberg_namespace_path import (
    iceberg_namespace_path,
)
from context.catalog.adapter.outbound.shared.polaris.raise_for_paged_listing import (
    raise_for_paged_listing,
)

if TYPE_CHECKING:
    from context.catalog.adapter.outbound.shared.polaris.polaris_http_client import PolarisHttpClient

_SEPARATOR = "\x1f"


def walk_iceberg_namespaces(polaris: PolarisHttpClient) -> list[tuple[str, tuple[str, ...]]]:
    """Return ``(catalog, parts)`` for every namespace of every catalog, each level after its parent.

    A paged listing at any level raises CatalogUnavailableError rather than skip namespaces.
    """
    found: list[tuple[str, tuple[str, ...]]] = []
    catalogs = polaris.management_request("GET", "/catalogs").json().get("catalogs", [])
    pending: list[tuple[str, tuple[str, ...]]] = [(str(catalog["name"]), ()) for catalog in catalogs]
    while pending:
        catalog, parent = pending.pop(0)
        params = {"parent": _SEPARATOR.join(parent)} if parent else None
        body = polaris.catalog_request("GET", iceberg_namespace_path(catalog), params=params).json()
        raise_for_paged_listing(body)
        for parts in body.get("namespaces", []):
            child = (catalog, tuple(str(part) for part in parts))
            found.append(child)
            pending.append(child)
    return found
