"""Define the RecordMaintenanceOperationResultService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.maintenance_run.maintenance_run_id import (
    MaintenanceRunId,
)
from application.domain.model.managed_table.table_status import TableStatus
from application.exceptions import ConflictError, NotFoundError, ValidationError
from application.port.inbound.maintenance_run.record_maintenance_operation_result import (
    RecordMaintenanceOperationResultUseCase,
    RecordMaintenanceOperationResultUseCaseInput,
    RecordMaintenanceOperationResultUseCaseOutput,
)
from application.service.translate_domain_errors import translate_domain_errors

if TYPE_CHECKING:
    from application.domain.model.maintenance_run.operation_run import OperationRun
    from application.domain.model.managed_table.table_uuid import TableUuid
    from application.port.outbound.maintenance_run.maintenance_runs_repo import (
        MaintenanceRunsRepo,
    )
    from application.port.outbound.managed_table.managed_tables_repo import (
        ManagedTablesRepo,
    )

_UNKNOWN_ERROR = "unknown error"


class RecordMaintenanceOperationResultService(RecordMaintenanceOperationResultUseCase):
    """Record the outcome of an operation attempt on the run and the table."""

    def __init__(
        self, runs_repo: MaintenanceRunsRepo, tables_repo: ManagedTablesRepo
    ) -> None:
        """Bind the repos."""
        self._runs_repo = runs_repo
        self._tables_repo = tables_repo

    def execute(
        self, request: RecordMaintenanceOperationResultUseCaseInput
    ) -> RecordMaintenanceOperationResultUseCaseOutput:
        """Update the run, then the table's backoff state.

        Two aggregates are updated in sequence, not atomically: the run is saved
        first, so a crash in between at worst loses one backoff update. A stale
        lower attempt, or a replay of an outcome already recorded, changes neither
        aggregate beyond what the run already holds.
        """
        try:
            operation = MaintenanceOperation(request.operation)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        run = self._runs_repo.get(MaintenanceRunId(request.run_id))
        if run is None:
            raise NotFoundError(f"maintenance run {request.run_id} not found")
        with translate_domain_errors():
            current = next(
                (op for op in run.operations if op.operation == operation), None
            )
            if current is None:
                raise ConflictError(
                    f"operation {operation} is not part of run {request.run_id}"
                )
            if request.attempt >= current.attempts and not _already_recorded(
                current, request
            ):
                if request.succeeded:
                    run.succeed(
                        operation, request.attempt, request.metrics, request.now
                    )
                else:
                    run.fail(
                        operation,
                        request.attempt,
                        request.error or _UNKNOWN_ERROR,
                        request.now,
                    )
                self._runs_repo.update(run)
                self._record_on_table(run.table_uuid, operation, request)
        return RecordMaintenanceOperationResultUseCaseOutput(
            run_id=run.id.value, status=run.status.value
        )

    def _record_on_table(
        self,
        table_uuid: TableUuid,
        operation: MaintenanceOperation,
        request: RecordMaintenanceOperationResultUseCaseInput,
    ) -> None:
        table = self._tables_repo.get(table_uuid)
        if table is None or table.status == TableStatus.DROPPED:
            return
        table.record_operation_result(operation, request.succeeded, request.now)
        self._tables_repo.update(table)


def _already_recorded(
    current: OperationRun, request: RecordMaintenanceOperationResultUseCaseInput
) -> bool:
    outcome = "succeeded" if request.succeeded else "failed"
    return current.attempts == request.attempt and current.status.value == outcome
