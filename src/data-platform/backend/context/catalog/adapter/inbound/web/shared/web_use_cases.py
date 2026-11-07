"""Define the WebUseCases bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.catalog.application.port.inbound.catalog import (
        CreateCatalogUseCase,
        DeleteCatalogUseCase,
        GetCatalogUseCase,
        ListCatalogsUseCase,
        UpdateCatalogUseCase,
    )
    from context.catalog.application.port.inbound.generic_table import (
        CreateGenericTableUseCase,
        DeleteGenericTableUseCase,
        GetGenericTableUseCase,
        ListGenericTablesUseCase,
    )
    from context.catalog.application.port.inbound.namespace import (
        CreateNamespaceUseCase,
        DeleteNamespaceUseCase,
        GetNamespaceUseCase,
        ListNamespacesUseCase,
        UpdateNamespacePropertiesUseCase,
    )
    from context.catalog.application.port.inbound.table import (
        CreateTableUseCase,
        DeleteTableUseCase,
        GetTableUseCase,
        ListTablesUseCase,
        RenameTableUseCase,
        UpdateTablePropertiesUseCase,
    )
    from context.catalog.application.port.inbound.view import (
        CreateViewUseCase,
        DeleteViewUseCase,
        GetViewUseCase,
        ListViewsUseCase,
    )


@dataclass(frozen=True)
class WebUseCases:
    """Hold every catalog use case the web API calls; the composition root builds it."""

    list_catalogs: ListCatalogsUseCase
    get_catalog: GetCatalogUseCase
    create_catalog: CreateCatalogUseCase
    update_catalog: UpdateCatalogUseCase
    delete_catalog: DeleteCatalogUseCase
    list_namespaces: ListNamespacesUseCase
    get_namespace: GetNamespaceUseCase
    create_namespace: CreateNamespaceUseCase
    delete_namespace: DeleteNamespaceUseCase
    update_namespace_properties: UpdateNamespacePropertiesUseCase
    list_tables: ListTablesUseCase
    get_table: GetTableUseCase
    create_table: CreateTableUseCase
    delete_table: DeleteTableUseCase
    rename_table: RenameTableUseCase
    update_table_properties: UpdateTablePropertiesUseCase
    list_generic_tables: ListGenericTablesUseCase
    get_generic_table: GetGenericTableUseCase
    create_generic_table: CreateGenericTableUseCase
    delete_generic_table: DeleteGenericTableUseCase
    list_views: ListViewsUseCase
    get_view: GetViewUseCase
    create_view: CreateViewUseCase
    delete_view: DeleteViewUseCase
