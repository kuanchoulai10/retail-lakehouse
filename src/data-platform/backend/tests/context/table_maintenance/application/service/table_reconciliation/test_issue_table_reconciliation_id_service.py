"""Test IssueTableReconciliationIdService: the application issues a reconciliation's id."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import TableReconciliationId
from context.table_maintenance.application.port.inbound.table_reconciliation import (
    IssueTableReconciliationIdUseCaseInput,
)
from context.table_maintenance.application.service.table_reconciliation import IssueTableReconciliationIdService


def test_it_issues_a_fresh_reconciliation_id():
    """Each call issues a new ``rc-`` id, which the reconciliation id type accepts."""
    service = IssueTableReconciliationIdService()

    first = service.execute(IssueTableReconciliationIdUseCaseInput()).reconciliation_id
    second = service.execute(IssueTableReconciliationIdUseCaseInput()).reconciliation_id

    assert TableReconciliationId(first).value.startswith("rc-")
    assert first != second
