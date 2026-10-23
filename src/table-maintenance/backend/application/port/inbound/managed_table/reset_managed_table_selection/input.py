"""Define the ResetManagedTableSelectionUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResetManagedTableSelectionUseCaseInput:
    """Carry the request to hand a table back to discovery rules."""

    uuid: str
