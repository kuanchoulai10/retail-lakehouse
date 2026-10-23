"""Define the ProcessMaintenanceCallbackService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.maintenance_run.maintenance_run_id import (
    MaintenanceRunId,
)
from application.exceptions import NotFoundError, ValidationError
from application.port.inbound.maintenance_run.process_maintenance_callback import (
    ProcessMaintenanceCallbackUseCase,
    ProcessMaintenanceCallbackUseCaseInput,
    ProcessMaintenanceCallbackUseCaseOutput,
)
from application.port.outbound.workflow.send_maintenance_result import (
    SendMaintenanceResultGatewayInput,
)

if TYPE_CHECKING:
    from application.port.outbound.maintenance_run.maintenance_runs_repo import (
        MaintenanceRunsRepo,
    )
    from application.port.outbound.workflow.send_maintenance_result import (
        SendMaintenanceResultGateway,
    )


class ProcessMaintenanceCallbackService(ProcessMaintenanceCallbackUseCase):
    """Forward a Spark job callback to the maintenance workflow."""

    def __init__(
        self,
        runs_repo: MaintenanceRunsRepo,
        result_gateway: SendMaintenanceResultGateway,
    ) -> None:
        """Bind the repo and the result gateway."""
        self._runs_repo = runs_repo
        self._result_gateway = result_gateway

    def execute(
        self, request: ProcessMaintenanceCallbackUseCaseInput
    ) -> ProcessMaintenanceCallbackUseCaseOutput:
        """Forward the result of a known run; the workflow decides staleness."""
        try:
            operation = MaintenanceOperation(request.operation)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        if self._runs_repo.get(MaintenanceRunId(request.run_id)) is None:
            raise NotFoundError(f"maintenance run {request.run_id} not found")
        self._result_gateway.send(
            SendMaintenanceResultGatewayInput(
                run_id=request.run_id,
                operation=operation.value,
                attempt=request.attempt,
                succeeded=request.succeeded,
                metrics=dict(request.metrics),
                error=request.error,
            )
        )
        return ProcessMaintenanceCallbackUseCaseOutput(accepted=True)
