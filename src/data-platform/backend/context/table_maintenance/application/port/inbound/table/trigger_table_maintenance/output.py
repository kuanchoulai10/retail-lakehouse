"""Define the TriggerTableMaintenanceUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class TriggerTableMaintenanceUseCaseOutput(UseCaseOutput):
    """Report whether the trigger request was accepted."""

    accepted: bool
