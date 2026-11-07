"""Define the ListNamespacesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.port.inbound.namespace import (
    ListNamespacesUseCase,
    ListNamespacesUseCaseInput,
    ListNamespacesUseCaseOutput,
    ListNamespacesUseCaseOutputItem,
)
from context.catalog.application.port.outbound.namespace import CatalogId
from context.catalog.application.service.catalog import catalog_id_from_name
from context.catalog.application.service.namespace.namespace_id_from_parts import (
    namespace_id_from_parts,
)

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.namespace import NamespacesRepo


class ListNamespacesService(ListNamespacesUseCase):
    """List the direct children of a namespace, or the top level of a catalog."""

    def __init__(self, namespaces_repo: NamespacesRepo) -> None:
        """Bind the repo."""
        self._namespaces_repo = namespaces_repo

    def execute(self, request: ListNamespacesUseCaseInput) -> ListNamespacesUseCaseOutput:
        """Return the direct children of the parent; the parent follows the namespace part rules."""
        if request.parent:
            parent = namespace_id_from_parts(request.catalog, request.parent)
            catalog_id, parts = CatalogId.of(parent.catalog), parent.parts
        else:
            catalog_id, parts = catalog_id_from_name(request.catalog), ()
        found = self._namespaces_repo.list_in(catalog_id, parts)
        return ListNamespacesUseCaseOutput(
            items=[
                ListNamespacesUseCaseOutputItem(catalog=namespace.catalog, namespace=list(namespace.parts))
                for namespace in found
            ]
        )
