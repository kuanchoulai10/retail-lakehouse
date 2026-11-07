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
    from context.catalog.application.port.inbound.namespace import (
        CreateNamespaceUseCase,
        DeleteNamespaceUseCase,
        GetNamespaceUseCase,
        ListNamespacesUseCase,
        UpdateNamespacePropertiesUseCase,
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
