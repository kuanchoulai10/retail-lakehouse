"""Define the DeleteMaintenanceJobService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    TableMaintenanceRunId,
)
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    DeleteMaintenanceJobUseCase,
    DeleteMaintenanceJobUseCaseInput,
    DeleteMaintenanceJobUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    DeleteMaintenanceJobGatewayInput,
)
from context.table_maintenance.application.service.table_maintenance_run.require_run_operation import (
    require_run_operation,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        DeleteMaintenanceJobGateway,
        TableMaintenanceRunsRepo,
    )


class DeleteMaintenanceJobService(DeleteMaintenanceJobUseCase):
    """Delete the job of one attempt of a run."""

    def __init__(self, runs_repo: TableMaintenanceRunsRepo, delete_gateway: DeleteMaintenanceJobGateway) -> None:
        """Bind the runs repo and the delete gateway."""
        self._runs_repo = runs_repo
        self._delete_gateway = delete_gateway

    def execute(self, request: DeleteMaintenanceJobUseCaseInput) -> DeleteMaintenanceJobUseCaseOutput:
        """Validate the attempt and delete its job; a missing job is a no-op.

        An unknown run is not found, and an operation other than the run's is a conflict; neither deletes.
        """
        try:
            operation = MaintenanceOperation(request.operation)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        if request.attempt < 1:
            raise ValidationError(f"attempt must be >= 1, got {request.attempt}")
        run = self._runs_repo.get(TableMaintenanceRunId(request.run_id))
        if run is None:
            raise NotFoundError(f"maintenance run {request.run_id} not found")
        require_run_operation(run, operation)
        self._delete_gateway.delete(
            DeleteMaintenanceJobGatewayInput(
                run_id=request.run_id,
                operation=operation.value,
                attempt=request.attempt,
            )
        )
        return DeleteMaintenanceJobUseCaseOutput(
            run_id=request.run_id,
            operation=operation.value,
            attempt=request.attempt,
        )
