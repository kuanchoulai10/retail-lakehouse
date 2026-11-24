"""Define the GetMaintenanceJobStatusService."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    TableMaintenanceRunId,
)
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    GetMaintenanceJobStatusUseCase,
    GetMaintenanceJobStatusUseCaseInput,
    GetMaintenanceJobStatusUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ReadMaintenanceJobGatewayInput,
    ReadMaintenanceJobProcessesGatewayInput,
)
from context.table_maintenance.application.service.table_maintenance_run.require_run_operation import (
    require_run_operation,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        ReadMaintenanceJobGateway,
        ReadMaintenanceJobProcessesGateway,
        TableMaintenanceRunsRepo,
    )

logger = logging.getLogger(__name__)

_KNOWN_STATES = frozenset({"SUBMITTING", "PENDING", "RUNNING", "COMPLETED", "FAILED", "NOT_FOUND"})
_NOT_FOUND = "NOT_FOUND"


class GetMaintenanceJobStatusService(GetMaintenanceJobStatusUseCase):
    """Report the state of the job of one attempt of a run and when its coordinator started."""

    def __init__(
        self,
        runs_repo: TableMaintenanceRunsRepo,
        read_gateway: ReadMaintenanceJobGateway,
        processes_gateway: ReadMaintenanceJobProcessesGateway,
    ) -> None:
        """Bind the runs repo, the job read gateway and the processes read gateway."""
        self._runs_repo = runs_repo
        self._read_gateway = read_gateway
        self._processes_gateway = processes_gateway

    def execute(self, request: GetMaintenanceJobStatusUseCaseInput) -> GetMaintenanceJobStatusUseCaseOutput:
        """Return the gateway's state and error and the coordinator's start, rejecting an unknown state.

        A job that is gone reads no processes. Processes that cannot be read, or a coordinator start that is not a
        time, leave the coordinator start out (logged) and the state still answers. An unknown run is not
        found, and an operation other than the run's is a conflict; neither reads anything.
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
        result = self._read_gateway.read(
            ReadMaintenanceJobGatewayInput(
                run_id=request.run_id,
                operation=operation.value,
                attempt=request.attempt,
            )
        )
        if result.state not in _KNOWN_STATES:
            raise ValidationError(f"unknown maintenance job state {result.state!r}")
        started_running_at = None if result.state == _NOT_FOUND else self._started_running_at(request, operation)
        return GetMaintenanceJobStatusUseCaseOutput(
            state=result.state, error=result.error, started_running_at=started_running_at
        )

    def _started_running_at(
        self, request: GetMaintenanceJobStatusUseCaseInput, operation: MaintenanceOperation
    ) -> datetime | None:
        try:
            processes = self._processes_gateway.read(
                ReadMaintenanceJobProcessesGatewayInput(
                    run_id=request.run_id, operation=operation.value, attempt=request.attempt
                )
            )
            started = (
                None if processes.started_running_at is None else datetime.fromisoformat(processes.started_running_at)
            )
        except Exception:
            logger.exception(
                "cannot read the processes of attempt %s of %s in run %s; its coordinator start stays unknown",
                request.attempt,
                operation.value,
                request.run_id,
            )
            return None
        return started
