"""Define the ListGenericTablesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.port.inbound.generic_table import (
    ListGenericTablesUseCase,
    ListGenericTablesUseCaseInput,
    ListGenericTablesUseCaseOutput,
    ListGenericTablesUseCaseOutputItem,
)
from context.catalog.application.service.namespace import namespace_id_from_parts

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.generic_table import GenericTablesRepo


class ListGenericTablesService(ListGenericTablesUseCase):
    """List the generic tables directly in a namespace."""

    def __init__(self, generic_tables_repo: GenericTablesRepo) -> None:
        """Bind the repo."""
        self._generic_tables_repo = generic_tables_repo

    def execute(self, request: ListGenericTablesUseCaseInput) -> ListGenericTablesUseCaseOutput:
        """Validate the namespace and return its generic tables' identities."""
        found = self._generic_tables_repo.list_in(namespace_id_from_parts(request.catalog, request.namespace))
        return ListGenericTablesUseCaseOutput(
            items=[
                ListGenericTablesUseCaseOutputItem(catalog=t.catalog, namespace=list(t.namespace), name=t.name)
                for t in found
            ]
        )
