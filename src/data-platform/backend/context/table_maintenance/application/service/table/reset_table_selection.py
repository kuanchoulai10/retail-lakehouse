"""Define the ResetTableSelectionService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import (
    TableChange,
    TableId,
)
from context.table_maintenance.application.domain.service.table_discovery_rule import (
    match_table_discovery_rule,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table import (
    ResetTableSelectionUseCase,
    ResetTableSelectionUseCaseInput,
    ResetTableSelectionUseCaseOutput,
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

    from context.table_maintenance.application.port.outbound.table_discovery_rule import (
        TableDiscoveryRulesRepo,
    )
    from context.table_maintenance.application.port.outbound.table import (
        TablesRepo,
        SendTableChangeGateway,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_preset import (
        TableMaintenancePresetsRepo,
    )


class ResetTableSelectionService(ResetTableSelectionUseCase):
    """Hand a table back to discovery rules and apply the current decision."""

    def __init__(  # noqa: PLR0913
        self,
        tables_repo: TablesRepo,
        rules_repo: TableDiscoveryRulesRepo,
        presets_repo: TableMaintenancePresetsRepo,
        table_change_gateway: SendTableChangeGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repos, the table change gateway and the clock."""
        self._tables_repo = tables_repo
        self._rules_repo = rules_repo
        self._presets_repo = presets_repo
        self._table_change_gateway = table_change_gateway
        self._clock = clock

    def execute(
        self, request: ResetTableSelectionUseCaseInput
    ) -> ResetTableSelectionUseCaseOutput:
        """Re-run rule matching for the table, whether or not discovery is enabled."""
        table = self._tables_repo.get(TableId(request.uuid))
        if table is None:
            raise NotFoundError(f"table {request.uuid} not found")
        now = self._clock()
        with translate_domain_errors():
            table.reset_to_auto(now)
            rule = match_table_discovery_rule(self._rules_repo.list_all(), table.name)
            if rule is None:
                table.apply_auto_decision(None, None, None, now)
            elif rule.preset_id is None:
                table.apply_auto_decision(rule.id, None, None, now)
            else:
                preset = self._presets_repo.get(rule.preset_id)
                if preset is None:
                    raise NotFoundError(
                        f"table maintenance preset {rule.preset_id} of rule {rule.id} "
                        "not found"
                    )
                table.apply_auto_decision(rule.id, preset.id, preset.settings, now)
            self._tables_repo.update(table)
        self._table_change_gateway.send(
            SendTableChangeGatewayInput(
                table_uuid=table.id.value,
                table_name=table.name.fully_qualified(),
                change=(
                    TableChange.RESUMED if table.is_enrolled else TableChange.STOPPED
                ).value,
                is_enrolled=table.is_enrolled,
            )
        )
        return ResetTableSelectionUseCaseOutput(**table_output_fields(table))
