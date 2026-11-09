"""Define the ListTableReconciliationsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_reconciliation.list_table_reconciliations.input import (
    ListTableReconciliationsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_reconciliation.list_table_reconciliations.output import (
    ListTableReconciliationsUseCaseOutput,
)


class ListTableReconciliationsUseCase(
    UseCase[ListTableReconciliationsUseCaseInput, ListTableReconciliationsUseCaseOutput]
):
    """List the reconciliations of a table."""

    @abstractmethod
    def execute(self, request: ListTableReconciliationsUseCaseInput) -> ListTableReconciliationsUseCaseOutput:
        """List the reconciliations of a table, newest first."""
