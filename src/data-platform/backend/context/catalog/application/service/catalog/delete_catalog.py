"""Define the DeleteCatalogService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.domain.model.catalog import CatalogId
from context.catalog.application.exceptions import NotFoundError
from context.catalog.application.port.inbound.catalog import (
    DeleteCatalogUseCase,
    DeleteCatalogUseCaseInput,
    DeleteCatalogUseCaseOutput,
)

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.catalog import CatalogsRepo


class DeleteCatalogService(DeleteCatalogUseCase):
    """Delete an empty catalog; one that still holds namespaces is refused, never emptied."""

    def __init__(self, catalogs_repo: CatalogsRepo) -> None:
        """Bind the repo."""
        self._catalogs_repo = catalogs_repo

    def execute(self, request: DeleteCatalogUseCaseInput) -> DeleteCatalogUseCaseOutput:
        """Delete the catalog or raise NotFoundError."""
        catalog_id = CatalogId.of(request.name)
        if self._catalogs_repo.get(catalog_id) is None:
            raise NotFoundError(f"catalog {request.name} not found")
        self._catalogs_repo.delete(catalog_id)
        return DeleteCatalogUseCaseOutput()
