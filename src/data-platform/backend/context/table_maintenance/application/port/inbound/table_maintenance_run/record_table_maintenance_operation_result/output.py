"""Define the RecordTableMaintenanceOperationResultUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class RecordTableMaintenanceOperationResultUseCaseOutput(UseCaseOutput):
    """Carry the result of the request to record the result of a maintenance operation attempt.

    ``status`` is the run's status. ``failure_class``, ``next_step`` and ``next_size`` are what was decided
    for the attempt: why it failed, what follows it, and at which size the next attempt runs.
    """

    run_id: str
    status: str
    failure_class: str | None = None
    next_step: str | None = None
    next_size: str | None = None
