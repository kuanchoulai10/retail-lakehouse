"""Define the TriggerTableMaintenanceService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.shared.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.table.table_change import TableChange
from application.domain.model.table.table_id import TableId
from application.exceptions import ConflictError, NotFoundError, ValidationError
from application.port.inbound.table.trigger_table_maintenance import (
    TriggerTableMaintenanceUseCase,
    TriggerTableMaintenanceUseCaseInput,
    TriggerTableMaintenanceUseCaseOutput,
)
from application.port.outbound.table.send_table_change import (
    SendTableChangeGatewayInput,
)

if TYPE_CHECKING:
    from application.port.outbound.table.tables_repo import (
        TablesRepo,
    )
    from application.port.outbound.table.send_table_change import (
        SendTableChangeGateway,
    )


class TriggerTableMaintenanceService(TriggerTableMaintenanceUseCase):
    """Ask a table's workflow to run the given operations now."""

    def __init__(
        self, tables_repo: TablesRepo, table_change_gateway: SendTableChangeGateway
    ) -> None:
        """Bind the repo and the table change gateway."""
        self._tables_repo = tables_repo
        self._table_change_gateway = table_change_gateway

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
        if not table.is_enrolled:
            raise ConflictError(
                f"table {request.uuid} is {table.status.value} and cannot be maintained"
            )
        self._table_change_gateway.send(
            SendTableChangeGatewayInput(
                table_uuid=table.id.value,
                table_name=table.name.fully_qualified(),
                change=TableChange.MAINTENANCE_REQUESTED.value,
                is_enrolled=table.is_enrolled,
                operations=[
                    op.value for op in MaintenanceOperation.ordered() if op in requested
                ],
            )
        )
        return TriggerTableMaintenanceUseCaseOutput(accepted=True)
