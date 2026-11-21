"""Define the SkipTableMaintenanceRunUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class SkipTableMaintenanceRunUseCaseOutput(UseCaseOutput):
    """Carry the run's status after the request and whether the request skipped it.

    ``skipped`` is False for a run that was no longer pending, which the request left alone.
    """

    run_id: str
    status: str
    skipped: bool
