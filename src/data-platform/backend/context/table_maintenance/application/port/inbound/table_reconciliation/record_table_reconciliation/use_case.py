"""Define the RecordTableReconciliationUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_reconciliation.record_table_reconciliation.input import (  # noqa: E501
    RecordTableReconciliationUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_reconciliation.record_table_reconciliation.output import (  # noqa: E501
    RecordTableReconciliationUseCaseOutput,
)


class RecordTableReconciliationUseCase(
    UseCase[RecordTableReconciliationUseCaseInput, RecordTableReconciliationUseCaseOutput]
):
    """Record what one reconciliation pass measured and decided."""

    @abstractmethod
    def execute(self, request: RecordTableReconciliationUseCaseInput) -> RecordTableReconciliationUseCaseOutput:
        """Record the reconciliation."""
