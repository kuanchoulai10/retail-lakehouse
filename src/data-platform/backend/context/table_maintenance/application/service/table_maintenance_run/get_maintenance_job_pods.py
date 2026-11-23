"""Define the GetMaintenanceJobPodsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    TableMaintenanceRunId,
)
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    GetMaintenanceJobPodsUseCase,
    GetMaintenanceJobPodsUseCaseInput,
    GetMaintenanceJobPodsUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ReadMaintenanceJobPodsGatewayInput,
)
from context.table_maintenance.application.service.table_maintenance_run.require_run_operation import (
    require_run_operation,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        ReadMaintenanceJobPodsGateway,
        TableMaintenanceRunsRepo,
    )


class GetMaintenanceJobPodsService(GetMaintenanceJobPodsUseCase):
    """Report which pods of the job of one attempt of a run can still run."""

    def __init__(self, runs_repo: TableMaintenanceRunsRepo, pods_gateway: ReadMaintenanceJobPodsGateway) -> None:
        """Bind the runs repo and the pods gateway."""
        self._runs_repo = runs_repo
        self._pods_gateway = pods_gateway

    def execute(self, request: GetMaintenanceJobPodsUseCaseInput) -> GetMaintenanceJobPodsUseCaseOutput:
        """Validate the attempt and return the names of its live pods.

        An unknown run is not found, and an operation other than the run's is a conflict; neither reads pods.
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
        result = self._pods_gateway.read(
            ReadMaintenanceJobPodsGatewayInput(
                run_id=request.run_id,
                operation=operation.value,
                attempt=request.attempt,
            )
        )
        return GetMaintenanceJobPodsUseCaseOutput(live_pods=tuple(result.live_pods))
