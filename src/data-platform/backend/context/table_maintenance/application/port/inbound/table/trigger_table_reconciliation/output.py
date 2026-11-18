"""Define the TriggerTableReconciliationUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class TriggerTableReconciliationUseCaseOutput(UseCaseOutput):
    """Report whether the reconcile request was accepted."""

    accepted: bool
