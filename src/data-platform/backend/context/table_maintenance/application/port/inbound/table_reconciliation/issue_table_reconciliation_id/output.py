"""Define the IssueTableReconciliationIdUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class IssueTableReconciliationIdUseCaseOutput(UseCaseOutput):
    """Carry the new reconciliation id."""

    reconciliation_id: str
