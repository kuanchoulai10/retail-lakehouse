"""Define the TriggerMaintenanceUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TriggerMaintenanceUseCaseOutput:
    """Report whether the trigger request was accepted."""

    accepted: bool
