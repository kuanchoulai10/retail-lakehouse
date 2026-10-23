"""Define the UpdateManagedTableSettingsService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.maintenance.workflow_ids import SIGNAL_SETTINGS_CHANGED
from application.domain.model.managed_table.table_uuid import TableUuid
from application.exceptions import NotFoundError
from application.port.inbound.managed_table.update_managed_table_settings import (
    UpdateManagedTableSettingsUseCase,
    UpdateManagedTableSettingsUseCaseInput,
    UpdateManagedTableSettingsUseCaseOutput,
)
from application.port.outbound.workflow.send_table_signal import (
    SendTableSignalGatewayInput,
)
from application.service.maintenance_settings.maintenance_settings_from_dict import (
    maintenance_settings_from_dict,
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


class UpdateManagedTableSettingsService(UpdateManagedTableSettingsUseCase):
    """Replace a managed table's settings and tell its workflow."""

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
        self, request: UpdateManagedTableSettingsUseCaseInput
    ) -> UpdateManagedTableSettingsUseCaseOutput:
        """Save the new settings, then signal ``settings_changed``."""
        table = self._tables_repo.get(TableUuid(request.uuid))
        if table is None:
            raise NotFoundError(f"managed table {request.uuid} not found")
        settings = maintenance_settings_from_dict(request.settings)
        with translate_domain_errors():
            table.update_settings(settings, self._clock())
            self._tables_repo.update(table)
        self._signal_gateway.send(
            SendTableSignalGatewayInput(
                table_uuid=table.id.value,
                signal=SIGNAL_SETTINGS_CHANGED,
                start_if_missing=table.needs_reconcile_workflow,
            )
        )
        return UpdateManagedTableSettingsUseCaseOutput(
            **managed_table_output_fields(table)
        )
