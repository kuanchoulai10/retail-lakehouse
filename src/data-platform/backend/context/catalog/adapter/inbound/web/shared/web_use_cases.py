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


@dataclass(frozen=True)
class WebUseCases:
    """Hold every catalog use case the web API calls; the composition root builds it."""

    list_catalogs: ListCatalogsUseCase
    get_catalog: GetCatalogUseCase
    create_catalog: CreateCatalogUseCase
    update_catalog: UpdateCatalogUseCase
    delete_catalog: DeleteCatalogUseCase
