"""Define the TriggerTableMaintenanceUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TriggerTableMaintenanceUseCaseOutput:
    """Report whether the trigger request was accepted."""

    accepted: bool
