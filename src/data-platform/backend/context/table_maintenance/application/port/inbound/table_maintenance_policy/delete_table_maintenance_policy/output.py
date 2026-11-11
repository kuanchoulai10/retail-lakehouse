"""Define the DeleteTableMaintenancePolicyUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteTableMaintenancePolicyUseCaseOutput:
    """Signal completion; carries no data."""
