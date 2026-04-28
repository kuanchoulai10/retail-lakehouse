"""Define the ListNamespacesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound.catalog.list_namespaces.input import (
    ListNamespacesUseCaseInput,
)
from application.port.inbound.catalog.list_namespaces.output import (
    ListNamespacesUseCaseOutput,
)
from application.port.inbound.catalog.list_namespaces.use_case import (
    ListNamespacesUseCase,
)

if TYPE_CHECKING:
    from application.port.outbound.catalog.read_catalog.gateway import (
        ReadCatalogGateway,
    )


class ListNamespacesService(ListNamespacesUseCase):
    """List all namespaces by delegating to ReadCatalogGateway."""

    def __init__(self, reader: ReadCatalogGateway) -> None:
        """Initialize with the catalog reader port."""
        self._reader = reader

    def execute(
        self, request: ListNamespacesUseCaseInput
    ) -> ListNamespacesUseCaseOutput:
        """Return all namespace names."""
        namespaces = self._reader.list_namespaces()
        return ListNamespacesUseCaseOutput(namespaces=namespaces)
