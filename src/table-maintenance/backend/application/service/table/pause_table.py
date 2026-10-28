"""Define the PauseTableService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.maintenance.workflow_ids import SIGNAL_PAUSE
from application.domain.model.table.table_id import TableId
from application.exceptions import NotFoundError
from application.port.inbound.table.pause_table import (
    PauseTableUseCase,
    PauseTableUseCaseInput,
    PauseTableUseCaseOutput,
)
from application.port.outbound.workflow.send_table_signal import (
    SendTableSignalGatewayInput,
)
from application.service.table.table_output_fields import (
    table_output_fields,
)
from application.service.translate_domain_errors import translate_domain_errors

if TYPE_CHECKING:
    from collections.abc import Callable

    from application.port.outbound.table.tables_repo import (
        TablesRepo,
    )
    from application.port.outbound.workflow.send_table_signal import (
        SendTableSignalGateway,
    )


class PauseTableService(PauseTableUseCase):
    """Pause a table and tell its workflow."""

    def __init__(
        self,
        tables_repo: TablesRepo,
        signal_gateway: SendTableSignalGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repo, the signal gateway and the clock."""
        self._tables_repo = tables_repo
        self._signal_gateway = signal_gateway
        self._clock = clock

    def execute(self, request: PauseTableUseCaseInput) -> PauseTableUseCaseOutput:
        """Save the transition, then signal the workflow."""
        table = self._tables_repo.get(TableId(request.uuid))
        if table is None:
            raise NotFoundError(f"table {request.uuid} not found")
        with translate_domain_errors():
            table.pause(self._clock())
            self._tables_repo.update(table)
        self._signal_gateway.send(
            SendTableSignalGatewayInput(
                table_uuid=table.id.value,
                table_name=table.name.fully_qualified(),
                signal=SIGNAL_PAUSE,
            )
        )
        return PauseTableUseCaseOutput(**table_output_fields(table))
