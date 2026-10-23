"""Define the PauseManagedTableService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.maintenance.workflow_ids import SIGNAL_PAUSE
from application.domain.model.managed_table.table_uuid import TableUuid
from application.exceptions import NotFoundError
from application.port.inbound.managed_table.pause_managed_table import (
    PauseManagedTableUseCase,
    PauseManagedTableUseCaseInput,
    PauseManagedTableUseCaseOutput,
)
from application.port.outbound.workflow.send_table_signal import (
    SendTableSignalGatewayInput,
)
from application.service.managed_table.managed_table_output_fields import (
    managed_table_output_fields,
)
from application.service.translate_domain_errors import translate_domain_errors

if TYPE_CHECKING:
    from collections.abc import Callable

    from application.port.outbound.managed_table.managed_tables_repo import (
        ManagedTablesRepo,
    )
    from application.port.outbound.workflow.send_table_signal import (
        SendTableSignalGateway,
    )


class PauseManagedTableService(PauseManagedTableUseCase):
    """Pause a managed table and tell its workflow."""

    def __init__(
        self,
        tables_repo: ManagedTablesRepo,
        signal_gateway: SendTableSignalGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repo, the signal gateway and the clock."""
        self._tables_repo = tables_repo
        self._signal_gateway = signal_gateway
        self._clock = clock

    def execute(
        self, request: PauseManagedTableUseCaseInput
    ) -> PauseManagedTableUseCaseOutput:
        """Save the transition, then signal the workflow."""
        table = self._tables_repo.get(TableUuid(request.uuid))
        if table is None:
            raise NotFoundError(f"managed table {request.uuid} not found")
        with translate_domain_errors():
            table.pause(self._clock())
            self._tables_repo.update(table)
        self._signal_gateway.send(
            SendTableSignalGatewayInput(table_uuid=table.id.value, signal=SIGNAL_PAUSE)
        )
        return PauseManagedTableUseCaseOutput(**managed_table_output_fields(table))
