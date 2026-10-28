"""Define the ListTablesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.table.list_tables.input import (
    ListTablesUseCaseInput,
)
from application.port.inbound.table.list_tables.output import (
    ListTablesUseCaseOutput,
)
from base.use_case import UseCase


class ListTablesUseCase(UseCase[ListTablesUseCaseInput, ListTablesUseCaseOutput]):
    """List tables, optionally by status."""

    @abstractmethod
    def execute(self, request: ListTablesUseCaseInput) -> ListTablesUseCaseOutput:
        """List tables, optionally by status."""
