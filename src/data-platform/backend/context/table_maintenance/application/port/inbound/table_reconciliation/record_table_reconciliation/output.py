"""Define the RecordTableReconciliationUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class RecordTableReconciliationUseCaseOutput(UseCaseOutput):
    """Report whether the reconciliation was newly recorded or already existed."""

    recorded: bool
