"""Define the ListNamespacesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound.catalog.list_namespaces.input import ListNamespacesInput
from application.port.inbound.catalog.list_namespaces.output import ListNamespacesOutput
from application.port.inbound.catalog.list_namespaces.use_case import (
    ListNamespacesUseCase,
)

if TYPE_CHECKING:
    from application.port.outbound.catalog.catalog_reader import CatalogReader


class ListNamespacesService(ListNamespacesUseCase):
    """List all namespaces by delegating to CatalogReader."""

    def __init__(self, reader: CatalogReader) -> None:
        """Initialize with the catalog reader port."""
        self._reader = reader

    def execute(self, request: ListNamespacesInput) -> ListNamespacesOutput:
        """Return all namespace names."""
        namespaces = self._reader.list_namespaces()
        return ListNamespacesOutput(namespaces=namespaces)
