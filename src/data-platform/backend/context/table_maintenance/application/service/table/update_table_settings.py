"""Define the UpdateTableSettingsService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import (
    TableChange,
    TableId,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table import (
    UpdateTableSettingsUseCase,
    UpdateTableSettingsUseCaseInput,
    UpdateTableSettingsUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import (
    SendTableChangeGatewayInput,
)
from context.table_maintenance.application.service.shared import (
    maintenance_settings_from_dict,
    translate_domain_errors,
)
from context.table_maintenance.application.service.table.table_output_fields import (
    table_output_fields,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.table import (
        SendTableChangeGateway,
        TablesRepo,
    )


class UpdateTableSettingsService(UpdateTableSettingsUseCase):
    """Replace a table's settings and tell its workflow."""

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

    def execute(self, request: UpdateTableSettingsUseCaseInput) -> UpdateTableSettingsUseCaseOutput:
        """Save the new settings, then signal ``settings_changed``."""
        table = self._tables_repo.get(TableId(request.uuid))
        if table is None:
            raise NotFoundError(f"table {request.uuid} not found")
        settings = maintenance_settings_from_dict(request.settings)
        with translate_domain_errors():
            table.update_settings(settings, self._clock())
            self._tables_repo.update(table)
        self._table_change_gateway.send(
            SendTableChangeGatewayInput(
                table_uuid=table.id.value,
                table_name=table.name.fully_qualified(),
                change=TableChange.SETTINGS_CHANGED.value,
                is_enrolled=table.is_enrolled,
            )
        )
        return UpdateTableSettingsUseCaseOutput(**table_output_fields(table))
