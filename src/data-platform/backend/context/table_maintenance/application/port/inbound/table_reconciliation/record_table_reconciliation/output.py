"""Define the RecordTableReconciliationUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecordTableReconciliationUseCaseOutput:
    """Report whether the reconciliation was newly recorded or already existed."""

    recorded: bool
