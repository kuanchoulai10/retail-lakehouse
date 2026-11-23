"""Define the GetMaintenanceJobProcessesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    TableMaintenanceRunId,
)
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    GetMaintenanceJobProcessesUseCase,
    GetMaintenanceJobProcessesUseCaseInput,
    GetMaintenanceJobProcessesUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ReadMaintenanceJobProcessesGatewayInput,
)
from context.table_maintenance.application.service.table_maintenance_run.require_run_operation import (
    require_run_operation,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        ReadMaintenanceJobProcessesGateway,
        TableMaintenanceRunsRepo,
    )


class GetMaintenanceJobProcessesService(GetMaintenanceJobProcessesUseCase):
    """Report which processes of the job of one attempt of a run can still run."""

    def __init__(
        self, runs_repo: TableMaintenanceRunsRepo, processes_gateway: ReadMaintenanceJobProcessesGateway
    ) -> None:
        """Bind the runs repo and the processes gateway."""
        self._runs_repo = runs_repo
        self._processes_gateway = processes_gateway

    def execute(self, request: GetMaintenanceJobProcessesUseCaseInput) -> GetMaintenanceJobProcessesUseCaseOutput:
        """Validate the attempt and return the names of its live processes.

        An unknown run is not found, and an operation other than the run's is a conflict; neither reads processes.
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
        result = self._processes_gateway.read(
            ReadMaintenanceJobProcessesGatewayInput(
                run_id=request.run_id,
                operation=operation.value,
                attempt=request.attempt,
            )
        )
        return GetMaintenanceJobProcessesUseCaseOutput(live_processes=tuple(result.live_processes))
