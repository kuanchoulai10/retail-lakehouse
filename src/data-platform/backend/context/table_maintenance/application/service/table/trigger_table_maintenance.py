"""Define the TriggerTableMaintenanceService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    TableId,
    TablePriority,
)
from context.table_maintenance.application.domain.model.table import TableChange
from context.table_maintenance.application.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.port.inbound.table import (
    TriggerTableMaintenanceUseCase,
    TriggerTableMaintenanceUseCaseInput,
    TriggerTableMaintenanceUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import (
    SendTableChangeGatewayInput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import (
        SendTableChangeGateway,
        TablesRepo,
    )


class TriggerTableMaintenanceService(TriggerTableMaintenanceUseCase):
    """Ask a table's workflow to run the given operations now."""

    def __init__(self, tables_repo: TablesRepo, table_change_gateway: SendTableChangeGateway) -> None:
        """Bind the repo and the table change gateway."""
        self._tables_repo = tables_repo
        self._table_change_gateway = table_change_gateway

    def execute(self, request: TriggerTableMaintenanceUseCaseInput) -> TriggerTableMaintenanceUseCaseOutput:
        """Validate the operations and the priority, then signal ``trigger_now``."""
        if not request.operations:
            raise ValidationError("operations must not be empty")
        try:
            requested = {MaintenanceOperation(op) for op in request.operations}
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        if request.priority is not None:
            try:
                TablePriority(request.priority)
            except ValueError as exc:
                raise ValidationError(f"unknown priority {request.priority!r}; expected one of P0, P1, P2, P3") from exc
        table = self._tables_repo.get(TableId(request.uuid))
        if table is None:
            raise NotFoundError(f"table {request.uuid} not found")
        if not table.is_managed:
            raise ConflictError(f"table {request.uuid} is {table.status.value} and cannot be maintained")
        self._table_change_gateway.send(
            SendTableChangeGatewayInput(
                table_uuid=table.id.value,
                table_name=table.name.fully_qualified(),
                change=TableChange.MAINTENANCE_REQUESTED.value,
                is_managed=table.is_managed,
                operations=[op.value for op in MaintenanceOperation.ordered() if op in requested],
                priority=request.priority,
            )
        )
        return TriggerTableMaintenanceUseCaseOutput(accepted=True)
