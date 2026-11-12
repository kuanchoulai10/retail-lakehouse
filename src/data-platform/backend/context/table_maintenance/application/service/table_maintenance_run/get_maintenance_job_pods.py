"""Define the GetMaintenanceJobPodsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
)
from context.table_maintenance.application.exceptions import ValidationError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    GetMaintenanceJobPodsUseCase,
    GetMaintenanceJobPodsUseCaseInput,
    GetMaintenanceJobPodsUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ReadMaintenanceJobPodsGatewayInput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        ReadMaintenanceJobPodsGateway,
    )


class GetMaintenanceJobPodsService(GetMaintenanceJobPodsUseCase):
    """Report which pods of one operation attempt's job can still run."""

    def __init__(self, pods_gateway: ReadMaintenanceJobPodsGateway) -> None:
        """Bind the pods gateway."""
        self._pods_gateway = pods_gateway

    def execute(self, request: GetMaintenanceJobPodsUseCaseInput) -> GetMaintenanceJobPodsUseCaseOutput:
        """Validate the attempt and return the names of its live pods."""
        try:
            operation = MaintenanceOperation(request.operation)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        if request.attempt < 1:
            raise ValidationError(f"attempt must be >= 1, got {request.attempt}")
        result = self._pods_gateway.read(
            ReadMaintenanceJobPodsGatewayInput(
                run_id=request.run_id,
                operation=operation.value,
                attempt=request.attempt,
            )
        )
        return GetMaintenanceJobPodsUseCaseOutput(live_pods=tuple(result.live_pods))
