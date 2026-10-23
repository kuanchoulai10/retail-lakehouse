"""Define the GetMaintenanceJobStatusService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.exceptions import ValidationError
from application.port.inbound.reconcile.get_maintenance_job_status import (
    GetMaintenanceJobStatusUseCase,
    GetMaintenanceJobStatusUseCaseInput,
    GetMaintenanceJobStatusUseCaseOutput,
)
from application.port.outbound.spark.read_maintenance_job import (
    ReadMaintenanceJobGatewayInput,
)

if TYPE_CHECKING:
    from application.port.outbound.spark.read_maintenance_job import (
        ReadMaintenanceJobGateway,
    )

_KNOWN_STATES = frozenset({"PENDING", "RUNNING", "COMPLETED", "FAILED", "NOT_FOUND"})


class GetMaintenanceJobStatusService(GetMaintenanceJobStatusUseCase):
    """Report the state of a Spark maintenance job."""

    def __init__(self, read_gateway: ReadMaintenanceJobGateway) -> None:
        """Bind the read gateway."""
        self._read_gateway = read_gateway

    def execute(
        self, request: GetMaintenanceJobStatusUseCaseInput
    ) -> GetMaintenanceJobStatusUseCaseOutput:
        """Return the gateway's state and error, rejecting an unknown state."""
        result = self._read_gateway.read(
            ReadMaintenanceJobGatewayInput(app_name=request.app_name)
        )
        if result.state not in _KNOWN_STATES:
            raise ValidationError(f"unknown maintenance job state {result.state!r}")
        return GetMaintenanceJobStatusUseCaseOutput(
            state=result.state, error=result.error
        )
