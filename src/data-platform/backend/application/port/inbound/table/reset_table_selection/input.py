"""Define the ResetTableSelectionUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResetTableSelectionUseCaseInput:
    """Carry the request to hand a table back to discovery rules."""

    uuid: str
