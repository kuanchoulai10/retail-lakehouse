"""Define the TriggerMaintenanceUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TriggerMaintenanceUseCaseOutput:
    """Carry the result."""

    accepted: bool
