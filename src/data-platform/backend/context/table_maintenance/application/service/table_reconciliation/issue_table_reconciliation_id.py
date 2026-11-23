"""Define the IssueTableReconciliationIdService."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import TableReconciliationId
from context.table_maintenance.application.port.inbound.table_reconciliation import (
    IssueTableReconciliationIdUseCase,
    IssueTableReconciliationIdUseCaseInput,
    IssueTableReconciliationIdUseCaseOutput,
)


class IssueTableReconciliationIdService(IssueTableReconciliationIdUseCase):
    """Issue the id of a new table reconciliation."""

    def execute(self, request: IssueTableReconciliationIdUseCaseInput) -> IssueTableReconciliationIdUseCaseOutput:  # noqa: ARG002
        """Return a fresh ``rc-`` id."""
        return IssueTableReconciliationIdUseCaseOutput(reconciliation_id=TableReconciliationId.new().value)
