"""Define the RecordMaintenanceAttemptRunningService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import MaintenanceOperation, TableMaintenanceRunId
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    RecordMaintenanceAttemptRunningUseCase,
    RecordMaintenanceAttemptRunningUseCaseInput,
    RecordMaintenanceAttemptRunningUseCaseOutput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors
from context.table_maintenance.application.service.table_maintenance_run.require_run_operation import (
    require_run_operation,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run import TableMaintenanceRunsRepo


class RecordMaintenanceAttemptRunningService(RecordMaintenanceAttemptRunningUseCase):
    """Record that the driver of a run's attempt started running, so its queued time ends."""

    def __init__(self, runs_repo: TableMaintenanceRunsRepo) -> None:
        """Bind the runs repo."""
        self._runs_repo = runs_repo

    def execute(
        self, request: RecordMaintenanceAttemptRunningUseCaseInput
    ) -> RecordMaintenanceAttemptRunningUseCaseOutput:
        """Record the driver's start on the run and return the run's status and the attempt's running time.

        Repeating the report, or reporting an earlier attempt, changes nothing. A report naming an operation
        other than the run's is a conflict.
        """
        try:
            operation = MaintenanceOperation(request.operation)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        run = self._runs_repo.get(TableMaintenanceRunId(request.run_id))
        if run is None:
            raise NotFoundError(f"maintenance run {request.run_id} not found")
        require_run_operation(run, operation)
        with translate_domain_errors():
            run.record_attempt_running(request.attempt, request.started_running_at, request.now)
        self._runs_repo.update(run)
        record = run.attempt_record(request.attempt)
        return RecordMaintenanceAttemptRunningUseCaseOutput(
            status=run.status.value,
            started_running_at=record.started_running_at if record else None,
        )
