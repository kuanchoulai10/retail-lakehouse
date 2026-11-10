"""Define the CatalogsPolarisRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.adapter.outbound.catalog.polaris.catalog_from_polaris import (
    catalog_from_polaris,
)
from context.catalog.adapter.outbound.catalog.polaris.catalogs_from_polaris import (
    catalogs_from_polaris,
)
from context.catalog.adapter.outbound.catalog.polaris.connection_config_to_polaris import (
    connection_config_to_polaris,
)
from context.catalog.adapter.outbound.catalog.polaris.management_catalog_path import (
    management_catalog_path,
)
from context.catalog.adapter.outbound.catalog.polaris.storage_config_to_polaris import (
    storage_config_to_polaris,
)
from context.catalog.application.exceptions import NotFoundError
from context.catalog.application.port.outbound.catalog import CatalogsRepo

if TYPE_CHECKING:
    from base import EntityId
    from base.model import EntityId as ModelEntityId
    from context.catalog.adapter.outbound.shared.polaris import PolarisHttpClient
    from context.catalog.application.port.outbound.catalog import Catalog


class CatalogsPolarisRepo(CatalogsRepo):
    """Load and save catalogs through the Polaris management API; nothing is cached."""

    def __init__(self, polaris: PolarisHttpClient) -> None:
        """Bind the Polaris client."""
        self._polaris = polaris

    def create(self, entity: Catalog) -> Catalog:
        """POST the catalog and return it as Polaris saved it."""
        catalog: dict[str, object] = {
            "name": entity.name,
            "type": entity.type.value,
            "properties": dict(entity.properties),
            "storageConfigInfo": storage_config_to_polaris(entity.storage_config),
        }
        if entity.connection_config is not None:
            catalog["connectionConfigInfo"] = connection_config_to_polaris(entity.connection_config)
        body = {"catalog": catalog}
        response = self._polaris.management_request("POST", "/catalogs", json=body)
        return catalog_from_polaris(response, entity.name)

    def get(self, entity_id: EntityId | ModelEntityId) -> Catalog | None:
        """GET the catalog; Polaris's 404 means there is none."""
        try:
            response = self._polaris.management_request("GET", management_catalog_path(entity_id.value))
        except NotFoundError:
            return None
        return catalog_from_polaris(response, entity_id.value)

    def list_all(self) -> list[Catalog]:
        """GET every catalog."""
        response = self._polaris.management_request("GET", "/catalogs")
        return catalogs_from_polaris(response)

    def update(self, catalog: Catalog) -> Catalog:
        """PUT the change with the loaded version as ``currentEntityVersion``; Polaris's 409 is a conflict."""
        body = {
            "currentEntityVersion": catalog.entity_version,
            "properties": dict(catalog.properties),
            "storageConfigInfo": storage_config_to_polaris(catalog.storage_config),
        }
        response = self._polaris.management_request("PUT", management_catalog_path(catalog.name), json=body)
        return catalog_from_polaris(response, catalog.name)

    def delete(self, entity_id: EntityId | ModelEntityId) -> None:
        """DELETE the catalog; Polaris refuses one that is not empty."""
        self._polaris.management_request("DELETE", management_catalog_path(entity_id.value))
