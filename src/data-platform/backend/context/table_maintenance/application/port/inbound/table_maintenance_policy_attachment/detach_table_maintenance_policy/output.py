"""Define the DetachTableMaintenancePolicyUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DetachTableMaintenancePolicyUseCaseOutput:
    """Signal completion; carries no data."""
