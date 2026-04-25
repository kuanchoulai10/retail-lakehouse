"""Define the ListTablesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.application.port.inbound.catalog.list_tables.input import ListTablesInput
from core.application.port.inbound.catalog.list_tables.output import ListTablesOutput
from core.application.port.inbound.catalog.list_tables.use_case import ListTablesUseCase

if TYPE_CHECKING:
    from core.application.port.outbound.catalog.catalog_reader import CatalogReader


class ListTablesService(ListTablesUseCase):
    """List all tables in a namespace by delegating to CatalogReader."""

    def __init__(self, reader: CatalogReader) -> None:
        """Initialize with the catalog reader port."""
        self._reader = reader

    def execute(self, request: ListTablesInput) -> ListTablesOutput:
        """Return all table names in the namespace."""
        tables = self._reader.list_tables(request.namespace)
        return ListTablesOutput(tables=tables)
