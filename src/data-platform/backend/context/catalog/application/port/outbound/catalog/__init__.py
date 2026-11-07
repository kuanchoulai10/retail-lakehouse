"""Outbound ports for the catalog group."""

from __future__ import annotations

from context.catalog.application.domain.model.catalog import (
    Catalog,
    CatalogId,
    CatalogType,
    StorageConfig,
)
from context.catalog.application.port.outbound.catalog.catalogs_repo import CatalogsRepo
from context.catalog.application.port.outbound.catalog.create_catalog_content_grant.gateway import (
    CreateCatalogContentGrantGateway,
)
from context.catalog.application.port.outbound.catalog.create_catalog_content_grant.input import (
    CreateCatalogContentGrantGatewayInput,
)

__all__ = [
    "Catalog",
    "CatalogId",
    "CatalogType",
    "CatalogsRepo",
    "CreateCatalogContentGrantGateway",
    "CreateCatalogContentGrantGatewayInput",
    "StorageConfig",
]
