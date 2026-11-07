"""Define the DeleteMaintenanceJobService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
)
from context.table_maintenance.application.exceptions import ValidationError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    DeleteMaintenanceJobUseCase,
    DeleteMaintenanceJobUseCaseInput,
    DeleteMaintenanceJobUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    DeleteMaintenanceJobGatewayInput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        DeleteMaintenanceJobGateway,
    )


class DeleteMaintenanceJobService(DeleteMaintenanceJobUseCase):
    """Delete the job of one operation attempt."""

    def __init__(self, delete_gateway: DeleteMaintenanceJobGateway) -> None:
        """Bind the delete gateway."""
        self._delete_gateway = delete_gateway

    def execute(
        self, request: DeleteMaintenanceJobUseCaseInput
    ) -> DeleteMaintenanceJobUseCaseOutput:
        """Validate the attempt and delete its job; a missing job is a no-op."""
        try:
            operation = MaintenanceOperation(request.operation)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        if request.attempt < 1:
            raise ValidationError(f"attempt must be >= 1, got {request.attempt}")
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
