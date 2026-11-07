"""Define the GetMaintenanceJobStatusService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
)
from context.table_maintenance.application.exceptions import ValidationError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    GetMaintenanceJobStatusUseCase,
    GetMaintenanceJobStatusUseCaseInput,
    GetMaintenanceJobStatusUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ReadMaintenanceJobGatewayInput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        ReadMaintenanceJobGateway,
    )

_KNOWN_STATES = frozenset({"PENDING", "RUNNING", "COMPLETED", "FAILED", "NOT_FOUND"})


class GetMaintenanceJobStatusService(GetMaintenanceJobStatusUseCase):
    """Report the state of the job of one operation attempt."""

    def __init__(self, read_gateway: ReadMaintenanceJobGateway) -> None:
        """Bind the read gateway."""
        self._read_gateway = read_gateway

    def execute(self, request: GetMaintenanceJobStatusUseCaseInput) -> GetMaintenanceJobStatusUseCaseOutput:
        """Return the gateway's state and error, rejecting an unknown state."""
        try:
            operation = MaintenanceOperation(request.operation)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        if request.attempt < 1:
            raise ValidationError(f"attempt must be >= 1, got {request.attempt}")
        result = self._read_gateway.read(
            ReadMaintenanceJobGatewayInput(
                run_id=request.run_id,
                operation=operation.value,
                attempt=request.attempt,
            )
        )
        if result.state not in _KNOWN_STATES:
            raise ValidationError(f"unknown maintenance job state {result.state!r}")
        return GetMaintenanceJobStatusUseCaseOutput(state=result.state, error=result.error)
