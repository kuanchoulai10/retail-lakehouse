"""Define the TriggerTableReconciliationUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TriggerTableReconciliationUseCaseInput:
    """Carry the request to reconcile a table now."""

    uuid: str
