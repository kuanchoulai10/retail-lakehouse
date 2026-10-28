"""Define the ResumeTableService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.table.table_change import TableChange
from application.domain.model.table.table_id import TableId
from application.exceptions import NotFoundError
from application.port.inbound.table.resume_table import (
    ResumeTableUseCase,
    ResumeTableUseCaseInput,
    ResumeTableUseCaseOutput,
)
from application.port.outbound.table.send_table_change import (
    SendTableChangeGatewayInput,
)
from application.service.table.table_output_fields import (
    table_output_fields,
)
from application.service.shared.translate_domain_errors import translate_domain_errors

if TYPE_CHECKING:
    from collections.abc import Callable

    from application.port.outbound.table.tables_repo import (
        TablesRepo,
    )
    from application.port.outbound.table.send_table_change import (
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
