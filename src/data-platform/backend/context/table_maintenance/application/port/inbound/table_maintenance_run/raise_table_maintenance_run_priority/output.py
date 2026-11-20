"""Define the RaiseTableMaintenanceRunPriorityUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class RaiseTableMaintenanceRunPriorityUseCaseOutput(UseCaseOutput):
    """Carry the run's priority after the request and whether the request raised it."""

    priority: str
    raised: bool
