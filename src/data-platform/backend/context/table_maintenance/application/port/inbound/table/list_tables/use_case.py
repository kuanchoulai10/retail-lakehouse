"""Define the ListTablesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table.list_tables.input import (
    ListTablesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table.list_tables.output import (
    ListTablesUseCaseOutput,
)


class ListTablesUseCase(UseCase[ListTablesUseCaseInput, ListTablesUseCaseOutput]):
    """List tables, optionally by status."""

    @abstractmethod
    def execute(self, request: ListTablesUseCaseInput) -> ListTablesUseCaseOutput:
        """List tables, optionally by status."""
