"""Define the GetMaintenanceJobStatusService."""

from __future__ import annotations

import logging
from datetime import datetime
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
    ReadMaintenanceJobPodsGatewayInput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        ReadMaintenanceJobGateway,
        ReadMaintenanceJobPodsGateway,
    )

logger = logging.getLogger(__name__)

_KNOWN_STATES = frozenset({"PENDING", "RUNNING", "COMPLETED", "FAILED", "NOT_FOUND"})
_NOT_FOUND = "NOT_FOUND"


class GetMaintenanceJobStatusService(GetMaintenanceJobStatusUseCase):
    """Report the state of the job of one operation attempt and when its driver started."""

    def __init__(self, read_gateway: ReadMaintenanceJobGateway, pods_gateway: ReadMaintenanceJobPodsGateway) -> None:
        """Bind the job read gateway and the pods read gateway."""
        self._read_gateway = read_gateway
        self._pods_gateway = pods_gateway

    def execute(self, request: GetMaintenanceJobStatusUseCaseInput) -> GetMaintenanceJobStatusUseCaseOutput:
        """Return the gateway's state and error and the driver's start, rejecting an unknown state.

        A job that is gone reads no pods. Pods that cannot be read, or a driver start that is not a
        time, leave the driver start out (logged) and the state still answers.
        """
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
        driver_started_at = None if result.state == _NOT_FOUND else self._driver_started_at(request, operation)
        return GetMaintenanceJobStatusUseCaseOutput(
            state=result.state, error=result.error, driver_started_at=driver_started_at
        )

    def _driver_started_at(
        self, request: GetMaintenanceJobStatusUseCaseInput, operation: MaintenanceOperation
    ) -> datetime | None:
        try:
            pods = self._pods_gateway.read(
                ReadMaintenanceJobPodsGatewayInput(
                    run_id=request.run_id, operation=operation.value, attempt=request.attempt
                )
            )
            started = None if pods.driver_started_at is None else datetime.fromisoformat(pods.driver_started_at)
        except Exception:
            logger.exception(
                "cannot read the pods of attempt %s of %s in run %s; its driver start stays unknown",
                request.attempt,
                operation.value,
                request.run_id,
            )
            return None
        return started
