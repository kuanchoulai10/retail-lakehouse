"""Define the TriggerTableMaintenanceService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.shared.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.shared.workflow_ids import SIGNAL_TRIGGER_NOW
from application.domain.model.table.table_id import TableId
from application.exceptions import ConflictError, NotFoundError, ValidationError
from application.port.inbound.table.trigger_table_maintenance import (
    TriggerTableMaintenanceUseCase,
    TriggerTableMaintenanceUseCaseInput,
    TriggerTableMaintenanceUseCaseOutput,
)
from application.port.outbound.workflow.send_table_signal import (
    SendTableSignalGatewayInput,
)

if TYPE_CHECKING:
    from application.port.outbound.table.tables_repo import (
        TablesRepo,
    )
    from application.port.outbound.workflow.send_table_signal import (
        SendTableSignalGateway,
    )


class TriggerTableMaintenanceService(TriggerTableMaintenanceUseCase):
    """Ask a table's workflow to run the given operations now."""

    def __init__(
        self, tables_repo: TablesRepo, signal_gateway: SendTableSignalGateway
    ) -> None:
        """Bind the repo and the signal gateway."""
        self._tables_repo = tables_repo
        self._signal_gateway = signal_gateway

    def execute(
        self, request: TriggerTableMaintenanceUseCaseInput
    ) -> TriggerTableMaintenanceUseCaseOutput:
        """Validate the operations, then signal ``trigger_now``."""
        if not request.operations:
            raise ValidationError("operations must not be empty")
        try:
            requested = {MaintenanceOperation(op) for op in request.operations}
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        table = self._tables_repo.get(TableId(request.uuid))
        if table is None:
            raise NotFoundError(f"table {request.uuid} not found")
        if not table.needs_reconcile_workflow:
            raise ConflictError(
                f"table {request.uuid} is {table.status.value} and cannot be maintained"
            )
        self._signal_gateway.send(
            SendTableSignalGatewayInput(
                table_uuid=table.id.value,
                table_name=table.name.fully_qualified(),
                signal=SIGNAL_TRIGGER_NOW,
                payload={
                    "operations": [
                        op.value
                        for op in MaintenanceOperation.ordered()
                        if op in requested
                    ]
                },
                start_if_missing=True,
            )
        )
        return TriggerTableMaintenanceUseCaseOutput(accepted=True)
