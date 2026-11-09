"""Define the TriggerTableReconciliationService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import (
    TableChange,
    TableId,
)
from context.table_maintenance.application.exceptions import (
    ConflictError,
    NotFoundError,
)
from context.table_maintenance.application.port.inbound.table import (
    TriggerTableReconciliationUseCase,
    TriggerTableReconciliationUseCaseInput,
    TriggerTableReconciliationUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import (
    SendTableChangeGatewayInput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import (
        SendTableChangeGateway,
        TablesRepo,
    )


class TriggerTableReconciliationService(TriggerTableReconciliationUseCase):
    """Ask a table's workflow to reconcile now, after any run in flight."""

    def __init__(self, tables_repo: TablesRepo, table_change_gateway: SendTableChangeGateway) -> None:
        """Bind the repo and the table change gateway."""
        self._tables_repo = tables_repo
        self._table_change_gateway = table_change_gateway

    def execute(self, request: TriggerTableReconciliationUseCaseInput) -> TriggerTableReconciliationUseCaseOutput:
        """Check the table is enrolled, then send a reconcile request."""
        table = self._tables_repo.get(TableId(request.uuid))
        if table is None:
            raise NotFoundError(f"table {request.uuid} not found")
        if not table.is_enrolled:
            raise ConflictError(f"table {request.uuid} is {table.status.value} and cannot be reconciled")
        self._table_change_gateway.send(
            SendTableChangeGatewayInput(
                table_uuid=table.id.value,
                table_name=table.name.fully_qualified(),
                change=TableChange.RECONCILE_REQUESTED.value,
                is_enrolled=table.is_enrolled,
                operations=[],
            )
        )
        return TriggerTableReconciliationUseCaseOutput(accepted=True)
