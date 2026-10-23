"""Define the DeleteMaintenanceJobService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.service.spark_application_name import spark_application_name
from application.exceptions import ValidationError
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
    """Delete the Spark job of one operation attempt."""

    def __init__(self, delete_gateway: DeleteMaintenanceJobGateway) -> None:
        """Bind the delete gateway."""
        self._delete_gateway = delete_gateway

    def execute(
        self, request: DeleteMaintenanceJobUseCaseInput
    ) -> DeleteMaintenanceJobUseCaseOutput:
        """Derive the attempt's application name, as submit does, and delete it."""
        try:
            operation = MaintenanceOperation(request.operation)
            app_name = spark_application_name(
                request.run_id, operation, request.attempt
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        self._delete_gateway.delete(DeleteMaintenanceJobGatewayInput(app_name=app_name))
        return DeleteMaintenanceJobUseCaseOutput(app_name=app_name)
