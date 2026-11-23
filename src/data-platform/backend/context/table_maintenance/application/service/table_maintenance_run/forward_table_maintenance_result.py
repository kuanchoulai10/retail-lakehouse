"""Define the ForwardTableMaintenanceResultService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    TableMaintenanceRunId,
)
from context.table_maintenance.application.exceptions import (
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    ForwardTableMaintenanceResultUseCase,
    ForwardTableMaintenanceResultUseCaseInput,
    ForwardTableMaintenanceResultUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    SendMaintenanceResultGatewayInput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        SendMaintenanceResultGateway,
        TableMaintenanceRunsRepo,
    )


class ForwardTableMaintenanceResultService(ForwardTableMaintenanceResultUseCase):
    """Forward the result a maintenance job reports to the table maintenance workflow."""

    def __init__(
        self,
        runs_repo: TableMaintenanceRunsRepo,
        result_gateway: SendMaintenanceResultGateway,
    ) -> None:
        """Bind the repo and the result gateway."""
        self._runs_repo = runs_repo
        self._result_gateway = result_gateway

    def execute(self, request: ForwardTableMaintenanceResultUseCaseInput) -> ForwardTableMaintenanceResultUseCaseOutput:
        """Forward the result of a known run, as a result of the run's operation; the workflow decides staleness.

        A report that names an operation other than the run's is invalid and forwards nothing.
        """
        try:
            named = None if request.operation is None else MaintenanceOperation(request.operation)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        run = self._runs_repo.get(TableMaintenanceRunId(request.run_id))
        if run is None:
            raise NotFoundError(f"maintenance run {request.run_id} not found")
        if named is not None and named is not run.operation:
            raise ValidationError(f"the run's operation is {run.operation.value}, not {named.value}")
        self._result_gateway.send(
            SendMaintenanceResultGatewayInput(
                execution_ref=run.execution_ref,
                run_id=request.run_id,
                operation=run.operation.value,
                attempt=request.attempt,
                succeeded=request.succeeded,
                metrics=dict(request.metrics),
                error=request.error,
            )
        )
        return ForwardTableMaintenanceResultUseCaseOutput(accepted=True)
