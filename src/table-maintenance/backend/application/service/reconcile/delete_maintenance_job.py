"""Define the DeleteMaintenanceJobService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound.reconcile.delete_maintenance_job import (
    DeleteMaintenanceJobUseCase,
    DeleteMaintenanceJobUseCaseInput,
    DeleteMaintenanceJobUseCaseOutput,
)
from application.port.outbound.spark.delete_maintenance_job import (
    DeleteMaintenanceJobGatewayInput,
)

if TYPE_CHECKING:
    from application.port.outbound.spark.delete_maintenance_job import (
        DeleteMaintenanceJobGateway,
    )


class DeleteMaintenanceJobService(DeleteMaintenanceJobUseCase):
    """Delete a Spark maintenance job."""

    def __init__(self, delete_gateway: DeleteMaintenanceJobGateway) -> None:
        """Bind the delete gateway."""
        self._delete_gateway = delete_gateway

    def execute(
        self, request: DeleteMaintenanceJobUseCaseInput
    ) -> DeleteMaintenanceJobUseCaseOutput:
        """Delete the job through the gateway."""
        self._delete_gateway.delete(
            DeleteMaintenanceJobGatewayInput(app_name=request.app_name)
        )
        return DeleteMaintenanceJobUseCaseOutput(app_name=request.app_name)
