"""Provide the build_catalog_web_use_cases function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.adapter.inbound.web.shared import WebUseCases
from context.catalog.adapter.outbound.catalog.polaris import (
    CatalogsPolarisRepo,
    CreateCatalogContentGrantPolarisGateway,
)
from context.catalog.application.service.catalog import (
    CreateCatalogService,
    DeleteCatalogService,
    GetCatalogService,
    ListCatalogsService,
    UpdateCatalogService,
)

if TYPE_CHECKING:
    from context.catalog.adapter.outbound.shared.polaris import PolarisHttpClient


def build_catalog_web_use_cases(polaris: PolarisHttpClient) -> WebUseCases:
    """Wire the catalog use cases to their Polaris adapters, all sharing one client."""
    catalogs_repo = CatalogsPolarisRepo(polaris)
    return WebUseCases(
        list_catalogs=ListCatalogsService(catalogs_repo),
        get_catalog=GetCatalogService(catalogs_repo),
        create_catalog=CreateCatalogService(catalogs_repo, CreateCatalogContentGrantPolarisGateway(polaris)),
        update_catalog=UpdateCatalogService(catalogs_repo),
        delete_catalog=DeleteCatalogService(catalogs_repo),
    )
