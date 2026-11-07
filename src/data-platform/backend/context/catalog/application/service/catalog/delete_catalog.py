"""Define the DeleteCatalogService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.exceptions import NotFoundError
from context.catalog.application.port.inbound.catalog import (
    DeleteCatalogUseCase,
    DeleteCatalogUseCaseInput,
    DeleteCatalogUseCaseOutput,
)
from context.catalog.application.service.catalog.catalog_id_from_name import (
    catalog_id_from_name,
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
        catalog_id = catalog_id_from_name(request.name)
        if self._catalogs_repo.get(catalog_id) is None:
            raise NotFoundError(f"catalog {request.name} not found")
        self._catalogs_repo.delete(catalog_id)
        return DeleteCatalogUseCaseOutput()
