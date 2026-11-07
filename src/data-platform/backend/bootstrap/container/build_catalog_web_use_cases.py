"""Provide the build_catalog_web_use_cases function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.adapter.inbound.web.shared import WebUseCases
from context.catalog.adapter.outbound.catalog.polaris import (
    CatalogsPolarisRepo,
    CreateCatalogContentGrantPolarisGateway,
)
from context.catalog.adapter.outbound.namespace.polaris import NamespacesPolarisRepo
from context.catalog.adapter.outbound.table.polaris import TablesPolarisRepo
from context.catalog.application.service.catalog import (
    CreateCatalogService,
    DeleteCatalogService,
    GetCatalogService,
    ListCatalogsService,
    UpdateCatalogService,
)
from context.catalog.application.service.namespace import (
    CreateNamespaceService,
    DeleteNamespaceService,
    GetNamespaceService,
    ListNamespacesService,
    UpdateNamespacePropertiesService,
)
from context.catalog.application.service.table import (
    CreateTableService,
    DeleteTableService,
    GetTableService,
    ListTablesService,
    RenameTableService,
    UpdateTablePropertiesService,
)

if TYPE_CHECKING:
    from context.catalog.adapter.outbound.shared.polaris import PolarisHttpClient


def build_catalog_web_use_cases(polaris: PolarisHttpClient) -> WebUseCases:
    """Wire the catalog use cases to their Polaris adapters, all sharing one client."""
    catalogs_repo = CatalogsPolarisRepo(polaris)
    namespaces_repo = NamespacesPolarisRepo(polaris)
    tables_repo = TablesPolarisRepo(polaris)
    return WebUseCases(
        list_catalogs=ListCatalogsService(catalogs_repo),
        get_catalog=GetCatalogService(catalogs_repo),
        create_catalog=CreateCatalogService(catalogs_repo, CreateCatalogContentGrantPolarisGateway(polaris)),
        update_catalog=UpdateCatalogService(catalogs_repo),
        delete_catalog=DeleteCatalogService(catalogs_repo),
        list_namespaces=ListNamespacesService(namespaces_repo),
        get_namespace=GetNamespaceService(namespaces_repo),
        create_namespace=CreateNamespaceService(namespaces_repo),
        delete_namespace=DeleteNamespaceService(namespaces_repo),
        update_namespace_properties=UpdateNamespacePropertiesService(namespaces_repo),
        list_tables=ListTablesService(tables_repo),
        get_table=GetTableService(tables_repo),
        create_table=CreateTableService(tables_repo),
        delete_table=DeleteTableService(tables_repo),
        rename_table=RenameTableService(tables_repo),
        update_table_properties=UpdateTablePropertiesService(tables_repo),
    )
