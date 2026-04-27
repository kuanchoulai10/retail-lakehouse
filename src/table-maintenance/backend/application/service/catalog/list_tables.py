"""Define the ListTablesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound.catalog.list_tables.input import ListTablesInput
from application.port.inbound.catalog.list_tables.output import ListTablesOutput
from application.port.inbound.catalog.list_tables.use_case import ListTablesUseCase

if TYPE_CHECKING:
    from application.port.outbound.catalog.read_catalog_gateway import (
        ReadCatalogGateway,
    )


class ListTablesService(ListTablesUseCase):
    """List all tables in a namespace by delegating to ReadCatalogGateway."""

    def __init__(self, reader: ReadCatalogGateway) -> None:
        """Initialize with the catalog reader port."""
        self._reader = reader

    def execute(self, request: ListTablesInput) -> ListTablesOutput:
        """Return all table names in the namespace."""
        tables = self._reader.list_tables(request.namespace)
        return ListTablesOutput(tables=tables)
