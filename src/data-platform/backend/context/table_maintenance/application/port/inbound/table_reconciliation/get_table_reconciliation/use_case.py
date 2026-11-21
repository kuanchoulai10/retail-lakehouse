"""Define the GetTableReconciliationUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_reconciliation.get_table_reconciliation.input import (
    GetTableReconciliationUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_reconciliation.get_table_reconciliation.output import (
    GetTableReconciliationUseCaseOutput,
)


class GetTableReconciliationUseCase(UseCase[GetTableReconciliationUseCaseInput, GetTableReconciliationUseCaseOutput]):
    """Get one reconciliation of a table."""

    @abstractmethod
    def execute(self, request: GetTableReconciliationUseCaseInput) -> GetTableReconciliationUseCaseOutput:
        """Return the reconciliation, or raise NotFoundError."""
