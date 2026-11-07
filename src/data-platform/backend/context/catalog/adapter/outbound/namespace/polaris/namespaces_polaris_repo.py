"""Define the NamespacesPolarisRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.adapter.outbound.namespace.polaris.namespace_from_polaris import (
    namespace_from_polaris,
)
from context.catalog.adapter.outbound.shared.polaris import iceberg_namespace_path
from context.catalog.application.exceptions import NotFoundError
from context.catalog.application.port.outbound.namespace import (
    CatalogId,
    Namespace,
    NamespaceId,
    NamespacesRepo,
)

if TYPE_CHECKING:
    from base import EntityId
    from context.catalog.adapter.outbound.shared.polaris import PolarisHttpClient

_SEPARATOR = "\x1f"


class NamespacesPolarisRepo(NamespacesRepo):
    """Load and save namespaces through the Iceberg REST API of Polaris; nothing is cached."""

    def __init__(self, polaris: PolarisHttpClient) -> None:
        """Bind the Polaris client."""
        self._polaris = polaris

    def create(self, entity: Namespace) -> Namespace:
        """POST the namespace with its properties and return it as Polaris saved it."""
        body = {"namespace": list(entity.parts), "properties": dict(entity.properties)}
        response = self._polaris.catalog_request("POST", iceberg_namespace_path(entity.catalog), json=body)
        return namespace_from_polaris(entity.catalog, response.json())

    def get(self, entity_id: EntityId) -> Namespace | None:
        """GET the namespace; Polaris's 404 means there is none."""
        namespace_id = NamespaceId(entity_id.value)
        try:
            response = self._polaris.catalog_request(
                "GET", iceberg_namespace_path(namespace_id.catalog, namespace_id.parts)
            )
        except NotFoundError:
            return None
        return namespace_from_polaris(namespace_id.catalog, response.json())

    def list_in(self, catalog: CatalogId, parent: tuple[str, ...]) -> list[Namespace]:
        """GET the direct children of ``parent``; ``parent`` is sent joined by U+001F, and omitted at the top."""
        params = {"parent": _SEPARATOR.join(parent)} if parent else None
        response = self._polaris.catalog_request("GET", iceberg_namespace_path(catalog.name), params=params)
        return [
            namespace_from_polaris(catalog.name, {"namespace": parts, "properties": {}})
            for parts in response.json().get("namespaces", [])
        ]

    def list_all(self) -> list[Namespace]:
        """Walk every catalog and every level, reading each namespace for its properties."""
        catalogs = self._polaris.management_request("GET", "/catalogs").json().get("catalogs", [])
        found: list[Namespace] = []
        for catalog in catalogs:
            self._walk(CatalogId.of(catalog["name"]), (), found)
        return found

    def update_properties(self, entity_id: NamespaceId, updates: dict[str, str], removals: list[str]) -> Namespace:
        """POST the change to ``/properties``, then read the namespace back as saved."""
        path = iceberg_namespace_path(entity_id.catalog, entity_id.parts)
        self._polaris.catalog_request(
            "POST", f"{path}/properties", json={"removals": list(removals), "updates": dict(updates)}
        )
        saved = self.get(entity_id)
        if saved is None:
            raise NotFoundError(f"namespace {list(entity_id.parts)} not found in catalog {entity_id.catalog}")
        return saved

    def delete(self, entity_id: EntityId) -> None:
        """DELETE the namespace; Polaris refuses one that is not empty."""
        namespace_id = NamespaceId(entity_id.value)
        self._polaris.catalog_request("DELETE", iceberg_namespace_path(namespace_id.catalog, namespace_id.parts))

    def _walk(self, catalog: CatalogId, parent: tuple[str, ...], found: list[Namespace]) -> None:
        for child in self.list_in(catalog, parent):
            loaded = self.get(child.id)
            if loaded is not None:
                found.append(loaded)
                self._walk(catalog, child.parts, found)
