"""Define the RecordMaintenanceAttemptRunningService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRunId
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    RecordMaintenanceAttemptRunningUseCase,
    RecordMaintenanceAttemptRunningUseCaseInput,
    RecordMaintenanceAttemptRunningUseCaseOutput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run import TableMaintenanceRunsRepo


class RecordMaintenanceAttemptRunningService(RecordMaintenanceAttemptRunningUseCase):
    """Record that the driver of an operation attempt started running, so its queued time ends."""

    def __init__(self, runs_repo: TableMaintenanceRunsRepo) -> None:
        """Bind the runs repo."""
        self._runs_repo = runs_repo

    def execute(
        self, request: RecordMaintenanceAttemptRunningUseCaseInput
    ) -> RecordMaintenanceAttemptRunningUseCaseOutput:
        """Record the driver's start on the run and return the operation's status and the attempt's running time.

        Repeating the report, or reporting an earlier attempt, changes nothing.
        """
        try:
            operation = MaintenanceOperation(request.operation)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        run = self._runs_repo.get(TableMaintenanceRunId(request.run_id))
        if run is None:
            raise NotFoundError(f"maintenance run {request.run_id} not found")
        with translate_domain_errors():
            run.record_attempt_running(operation, request.attempt, request.started_running_at, request.now)
        self._runs_repo.update(run)
        record = run.attempt_record(operation, request.attempt)
        current = next(op for op in run.operations if op.operation == operation)
        return RecordMaintenanceAttemptRunningUseCaseOutput(
            status=current.status.value,
            started_running_at=record.started_running_at if record else None,
        )
