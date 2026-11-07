"""Define the ListTablesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.table.list_tables.input import (
    ListTablesUseCaseInput,
)
from context.catalog.application.port.inbound.table.list_tables.output import (
    ListTablesUseCaseOutput,
)


class ListTablesUseCase(UseCase[ListTablesUseCaseInput, ListTablesUseCaseOutput]):
    """List the Iceberg tables directly in a namespace."""

    @abstractmethod
    def execute(self, request: ListTablesUseCaseInput) -> ListTablesUseCaseOutput:
        """List the Iceberg tables directly in a namespace."""
