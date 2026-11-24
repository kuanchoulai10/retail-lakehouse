"""Provide drop_catalog, which removes whatever a scenario left of a catalog it created."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

if TYPE_CHECKING:
    from e2e.support.polaris_client import PolarisClient

_GONE = 404
_DROPPED = (204, 404)
_NAMESPACE_SEPARATOR = "\x1f"
CONTENT_GRANTS = ("CATALOG_MANAGE_CONTENT", "CATALOG_MANAGE_METADATA")


def drop_catalog(polaris: PolarisClient, catalog: str) -> None:
    """Delete the catalog's views, generic tables, tables, namespaces and own roles, then the catalog.

    The content grants go back on ``catalog_admin`` first, since a scenario may have revoked them
    and Polaris lets nobody empty the catalog without them. Tables are dropped without purging; the
    scenario removes the catalog's storage prefix itself. Raise ``RuntimeError`` when Polaris keeps the catalog.
    """
    name = _q(catalog)
    if polaris.management("GET", f"/catalogs/{name}").status_code == _GONE:
        return
    for privilege in CONTENT_GRANTS:
        polaris.management(
            "PUT",
            f"/catalogs/{name}/catalog-roles/catalog_admin/grants",
            {"grant": {"type": "catalog", "privilege": privilege}},
        )
    for parts in _namespaces_deepest_first(polaris, name, ()):
        namespace = _q(_NAMESPACE_SEPARATOR.join(parts))
        for prefix, kind, suffix in (
            ("/v1", "views", ""),
            ("/polaris/v1", "generic-tables", ""),
            ("/v1", "tables", "?purgeRequested=false"),
        ):
            listing = f"{prefix}/{name}/namespaces/{namespace}/{kind}"
            for identifier in polaris.catalog("GET", listing).json().get("identifiers", []):
                polaris.catalog("DELETE", f"{listing}/{_q(identifier['name'])}{suffix}")
        polaris.catalog("DELETE", f"/v1/{name}/namespaces/{namespace}")
    for role in polaris.management("GET", f"/catalogs/{name}/catalog-roles").json().get("roles", []):
        if role["name"] != "catalog_admin":
            polaris.management("DELETE", f"/catalogs/{name}/catalog-roles/{_q(role['name'])}")
    reply = polaris.management("DELETE", f"/catalogs/{name}")
    if reply.status_code not in _DROPPED:
        raise RuntimeError(f"catalog {catalog} was not dropped: {reply.status_code} {reply.text}")


def _namespaces_deepest_first(polaris: PolarisClient, catalog: str, parent: tuple[str, ...]) -> list[tuple[str, ...]]:
    query = f"?parent={_q(_NAMESPACE_SEPARATOR.join(parent))}" if parent else ""
    found: list[tuple[str, ...]] = []
    for child in polaris.catalog("GET", f"/v1/{catalog}/namespaces{query}").json().get("namespaces", []):
        found.extend(_namespaces_deepest_first(polaris, catalog, tuple(child)))
        found.append(tuple(child))
    return found


def _q(value: str) -> str:
    return quote(value, safe="")
