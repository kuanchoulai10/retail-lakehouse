"""Define the IssueTableReconciliationIdUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_reconciliation.issue_table_reconciliation_id.input import (  # noqa: E501
    IssueTableReconciliationIdUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_reconciliation.issue_table_reconciliation_id.output import (  # noqa: E501
    IssueTableReconciliationIdUseCaseOutput,
)


class IssueTableReconciliationIdUseCase(
    UseCase[IssueTableReconciliationIdUseCaseInput, IssueTableReconciliationIdUseCaseOutput]
):
    """Issue the id of a new table reconciliation."""

    @abstractmethod
    def execute(self, request: IssueTableReconciliationIdUseCaseInput) -> IssueTableReconciliationIdUseCaseOutput:
        """Issue the id of a new table reconciliation."""
