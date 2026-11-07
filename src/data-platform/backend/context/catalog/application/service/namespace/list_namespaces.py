"""Define the ListNamespacesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.exceptions import ValidationError
from context.catalog.application.port.inbound.namespace import (
    ListNamespacesUseCase,
    ListNamespacesUseCaseInput,
    ListNamespacesUseCaseOutput,
    ListNamespacesUseCaseOutputItem,
)
from context.catalog.application.port.outbound.namespace import CatalogId

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.namespace import NamespacesRepo


class ListNamespacesService(ListNamespacesUseCase):
    """List the direct children of a namespace, or the top level of a catalog."""

    def __init__(self, namespaces_repo: NamespacesRepo) -> None:
        """Bind the repo."""
        self._namespaces_repo = namespaces_repo

    def execute(self, request: ListNamespacesUseCaseInput) -> ListNamespacesUseCaseOutput:
        """Return the direct children of the parent."""
        if not request.catalog.strip():
            raise ValidationError("catalog name must not be blank")
        found = self._namespaces_repo.list_in(CatalogId.of(request.catalog), tuple(request.parent))
        return ListNamespacesUseCaseOutput(
            items=[
                ListNamespacesUseCaseOutputItem(catalog=namespace.catalog, namespace=list(namespace.parts))
                for namespace in found
            ]
        )
