"""Define the ListManagedTablesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.managed_table.list_managed_tables.input import (
    ListManagedTablesUseCaseInput,
)
from application.port.inbound.managed_table.list_managed_tables.output import (
    ListManagedTablesUseCaseOutput,
)
from base.use_case import UseCase


class ListManagedTablesUseCase(
    UseCase[ListManagedTablesUseCaseInput, ListManagedTablesUseCaseOutput]
):
    """List managed tables, optionally by status."""

    @abstractmethod
    def execute(
        self, request: ListManagedTablesUseCaseInput
    ) -> ListManagedTablesUseCaseOutput:
        """List managed tables, optionally by status."""
