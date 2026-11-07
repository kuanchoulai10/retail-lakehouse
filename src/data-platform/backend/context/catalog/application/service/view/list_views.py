"""Define the ListViewsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.port.inbound.view import (
    ListViewsUseCase,
    ListViewsUseCaseInput,
    ListViewsUseCaseOutput,
    ListViewsUseCaseOutputItem,
)
from context.catalog.application.service.namespace import namespace_id_from_parts

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.view import ViewsRepo


class ListViewsService(ListViewsUseCase):
    """List the Iceberg views directly in a namespace."""

    def __init__(self, views_repo: ViewsRepo) -> None:
        """Bind the repo."""
        self._views_repo = views_repo

    def execute(self, request: ListViewsUseCaseInput) -> ListViewsUseCaseOutput:
        """Validate the namespace and return its views' identities."""
        found = self._views_repo.list_in(namespace_id_from_parts(request.catalog, request.namespace))
        return ListViewsUseCaseOutput(
            items=[
                ListViewsUseCaseOutputItem(catalog=v.catalog, namespace=list(v.namespace), name=v.name) for v in found
            ]
        )
