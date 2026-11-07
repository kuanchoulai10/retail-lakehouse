"""Define the GetCatalogService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.exceptions import NotFoundError
from context.catalog.application.port.inbound.catalog import (
    GetCatalogUseCase,
    GetCatalogUseCaseInput,
    GetCatalogUseCaseOutput,
)
from context.catalog.application.service.catalog.catalog_id_from_name import (
    catalog_id_from_name,
)
from context.catalog.application.service.catalog.catalog_output_fields import (
    catalog_output_fields,
)

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.catalog import CatalogsRepo


class GetCatalogService(GetCatalogUseCase):
    """Get one catalog."""

    def __init__(self, catalogs_repo: CatalogsRepo) -> None:
        """Bind the repo."""
        self._catalogs_repo = catalogs_repo

    def execute(self, request: GetCatalogUseCaseInput) -> GetCatalogUseCaseOutput:
        """Return the catalog or raise NotFoundError."""
        catalog = self._catalogs_repo.get(catalog_id_from_name(request.name))
        if catalog is None:
            raise NotFoundError(f"catalog {request.name} not found")
        return GetCatalogUseCaseOutput(**catalog_output_fields(catalog))
