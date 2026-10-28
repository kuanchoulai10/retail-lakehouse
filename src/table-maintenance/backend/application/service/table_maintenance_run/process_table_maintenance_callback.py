"""Define the ProcessTableMaintenanceCallbackService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.shared.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.table_maintenance_run.table_maintenance_run_id import (
    TableMaintenanceRunId,
)
from application.exceptions import NotFoundError, ValidationError
from application.port.inbound.table_maintenance_run.process_table_maintenance_callback import (
    ProcessTableMaintenanceCallbackUseCase,
    ProcessTableMaintenanceCallbackUseCaseInput,
    ProcessTableMaintenanceCallbackUseCaseOutput,
)
from application.port.outbound.workflow.send_maintenance_result import (
    SendMaintenanceResultGatewayInput,
)

if TYPE_CHECKING:
    from application.port.outbound.table_maintenance_run.table_maintenance_runs_repo import (
        TableMaintenanceRunsRepo,
    )
    from application.port.outbound.workflow.send_maintenance_result import (
        SendMaintenanceResultGateway,
    )


class ProcessTableMaintenanceCallbackService(ProcessTableMaintenanceCallbackUseCase):
    """Forward a Spark job callback to the table maintenance workflow."""

    def __init__(
        self,
        runs_repo: TableMaintenanceRunsRepo,
        result_gateway: SendMaintenanceResultGateway,
    ) -> None:
        """Bind the repo and the result gateway."""
        self._runs_repo = runs_repo
        self._result_gateway = result_gateway

    def execute(
        self, request: ProcessTableMaintenanceCallbackUseCaseInput
    ) -> ProcessTableMaintenanceCallbackUseCaseOutput:
        """Forward the result of a known run; the workflow decides staleness."""
        try:
            operation = MaintenanceOperation(request.operation)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        run = self._runs_repo.get(TableMaintenanceRunId(request.run_id))
        if run is None:
            raise NotFoundError(f"maintenance run {request.run_id} not found")
        self._result_gateway.send(
            SendMaintenanceResultGatewayInput(
                execution_ref=run.execution_ref,
                run_id=request.run_id,
                operation=operation.value,
                attempt=request.attempt,
                succeeded=request.succeeded,
                metrics=dict(request.metrics),
                error=request.error,
            )
        )
        return ProcessTableMaintenanceCallbackUseCaseOutput(accepted=True)
