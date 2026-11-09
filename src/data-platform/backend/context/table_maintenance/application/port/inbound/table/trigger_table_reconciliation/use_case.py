"""Define the TriggerTableReconciliationUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table.trigger_table_reconciliation.input import (
    TriggerTableReconciliationUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table.trigger_table_reconciliation.output import (
    TriggerTableReconciliationUseCaseOutput,
)


class TriggerTableReconciliationUseCase(
    UseCase[TriggerTableReconciliationUseCaseInput, TriggerTableReconciliationUseCaseOutput]
):
    """Reconcile a table now by the normal rules."""

    @abstractmethod
    def execute(self, request: TriggerTableReconciliationUseCaseInput) -> TriggerTableReconciliationUseCaseOutput:
        """Reconcile a table now by the normal rules."""
