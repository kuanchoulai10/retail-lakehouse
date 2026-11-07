"""Define the ResumeTableService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import (
    TableChange,
    TableId,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table import (
    ResumeTableUseCase,
    ResumeTableUseCaseInput,
    ResumeTableUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import (
    SendTableChangeGatewayInput,
)
from context.table_maintenance.application.service.table.table_output_fields import (
    table_output_fields,
)
from context.table_maintenance.application.service.shared import translate_domain_errors

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.table import (
        TablesRepo,
        SendTableChangeGateway,
    )


class ResumeTableService(ResumeTableUseCase):
    """Resume a table and tell its workflow."""

    def __init__(
        self,
        tables_repo: TablesRepo,
        table_change_gateway: SendTableChangeGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repo, the table change gateway and the clock."""
        self._tables_repo = tables_repo
        self._table_change_gateway = table_change_gateway
        self._clock = clock

    def execute(self, request: ResumeTableUseCaseInput) -> ResumeTableUseCaseOutput:
        """Save the transition, then signal the workflow."""
        table = self._tables_repo.get(TableId(request.uuid))
        if table is None:
            raise NotFoundError(f"table {request.uuid} not found")
        with translate_domain_errors():
            table.resume(self._clock())
            self._tables_repo.update(table)
        self._table_change_gateway.send(
            SendTableChangeGatewayInput(
                table_uuid=table.id.value,
                table_name=table.name.fully_qualified(),
                change=TableChange.RESUMED.value,
                is_enrolled=table.is_enrolled,
            )
        )
        return ResumeTableUseCaseOutput(**table_output_fields(table))
