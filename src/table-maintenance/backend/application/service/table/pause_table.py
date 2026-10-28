"""Define the PauseTableService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.table import TableChange, TableId
from application.exceptions import NotFoundError
from application.port.inbound.table import (
    PauseTableUseCase,
    PauseTableUseCaseInput,
    PauseTableUseCaseOutput,
)
from application.port.outbound.table import SendTableChangeGatewayInput
from application.service.table.table_output_fields import (
    table_output_fields,
)
from application.service.shared import translate_domain_errors

if TYPE_CHECKING:
    from collections.abc import Callable

    from application.port.outbound.table import TablesRepo, SendTableChangeGateway


class PauseTableService(PauseTableUseCase):
    """Pause a table and tell its workflow."""

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

    def execute(self, request: PauseTableUseCaseInput) -> PauseTableUseCaseOutput:
        """Save the transition, then signal the workflow."""
        table = self._tables_repo.get(TableId(request.uuid))
        if table is None:
            raise NotFoundError(f"table {request.uuid} not found")
        with translate_domain_errors():
            table.pause(self._clock())
            self._tables_repo.update(table)
        self._table_change_gateway.send(
            SendTableChangeGatewayInput(
                table_uuid=table.id.value,
                table_name=table.name.fully_qualified(),
                change=TableChange.PAUSED.value,
                is_enrolled=table.is_enrolled,
            )
        )
        return PauseTableUseCaseOutput(**table_output_fields(table))
