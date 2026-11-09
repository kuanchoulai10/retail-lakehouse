"""Define the TriggerTableReconciliationUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TriggerTableReconciliationUseCaseOutput:
    """Report whether the reconcile request was accepted."""

    accepted: bool
