"""Define the ListCatalogsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.port.inbound.catalog import (
    ListCatalogsUseCase,
    ListCatalogsUseCaseInput,
    ListCatalogsUseCaseOutput,
    ListCatalogsUseCaseOutputItem,
)
from context.catalog.application.service.catalog.catalog_output_fields import (
    catalog_output_fields,
)

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.catalog import CatalogsRepo


class ListCatalogsService(ListCatalogsUseCase):
    """List every catalog."""

    def __init__(self, catalogs_repo: CatalogsRepo) -> None:
        """Bind the repo."""
        self._catalogs_repo = catalogs_repo

    def execute(self, request: ListCatalogsUseCaseInput) -> ListCatalogsUseCaseOutput:  # noqa: ARG002
        """Return every catalog the catalog service holds."""
        return ListCatalogsUseCaseOutput(
            items=[
                ListCatalogsUseCaseOutputItem(**catalog_output_fields(catalog))
                for catalog in self._catalogs_repo.list_all()
            ]
        )
