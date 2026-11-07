"""Define the walk_iceberg_namespaces function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.adapter.outbound.shared.polaris.iceberg_namespace_path import (
    iceberg_namespace_path,
)
from context.catalog.adapter.outbound.shared.polaris.listed_catalog_names import (
    listed_catalog_names,
)
from context.catalog.adapter.outbound.shared.polaris.listed_namespaces import listed_namespaces

if TYPE_CHECKING:
    from context.catalog.adapter.outbound.shared.polaris.polaris_http_client import PolarisHttpClient

_SEPARATOR = "\x1f"


def walk_iceberg_namespaces(polaris: PolarisHttpClient) -> list[tuple[str, tuple[str, ...]]]:
    """Return ``(catalog, parts)`` for every namespace of every catalog, each level after its parent.

    A reply this backend cannot read, or a paged listing, at any level raises
    CatalogUnavailableError rather than skip namespaces.
    """
    found: list[tuple[str, tuple[str, ...]]] = []
    catalogs = listed_catalog_names(polaris.management_request("GET", "/catalogs"))
    pending: list[tuple[str, tuple[str, ...]]] = [(catalog, ()) for catalog in catalogs]
    while pending:
        catalog, parent = pending.pop(0)
        params = {"parent": _SEPARATOR.join(parent)} if parent else None
        response = polaris.catalog_request("GET", iceberg_namespace_path(catalog), params=params)
        for parts in listed_namespaces(response, catalog):
            child = (catalog, parts)
            found.append(child)
            pending.append(child)
    return found
