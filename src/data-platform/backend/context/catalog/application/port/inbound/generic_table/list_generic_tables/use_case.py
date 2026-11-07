"""Define the ListGenericTablesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.generic_table.list_generic_tables.input import (
    ListGenericTablesUseCaseInput,
)
from context.catalog.application.port.inbound.generic_table.list_generic_tables.output import (
    ListGenericTablesUseCaseOutput,
)


class ListGenericTablesUseCase(UseCase[ListGenericTablesUseCaseInput, ListGenericTablesUseCaseOutput]):
    """List the generic tables directly in a namespace."""

    @abstractmethod
    def execute(self, request: ListGenericTablesUseCaseInput) -> ListGenericTablesUseCaseOutput:
        """List the generic tables directly in a namespace."""
