"""Define the ListTablesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.port.inbound.table import (
    ListTablesUseCase,
    ListTablesUseCaseInput,
    ListTablesUseCaseOutput,
    ListTablesUseCaseOutputItem,
)
from context.catalog.application.service.namespace import namespace_id_from_parts

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.table import TablesRepo


class ListTablesService(ListTablesUseCase):
    """List the Iceberg tables directly in a namespace."""

    def __init__(self, tables_repo: TablesRepo) -> None:
        """Bind the repo."""
        self._tables_repo = tables_repo

    def execute(self, request: ListTablesUseCaseInput) -> ListTablesUseCaseOutput:
        """Validate the namespace and return its tables' identities."""
        found = self._tables_repo.list_in(namespace_id_from_parts(request.catalog, request.namespace))
        return ListTablesUseCaseOutput(
            items=[
                ListTablesUseCaseOutputItem(catalog=t.catalog, namespace=list(t.namespace), name=t.name) for t in found
            ]
        )
