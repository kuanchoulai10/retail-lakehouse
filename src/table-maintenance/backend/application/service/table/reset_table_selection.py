"""Define the ResetTableSelectionService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.maintenance.workflow_ids import (
    SIGNAL_RESUME,
    SIGNAL_STOP,
)
from application.domain.model.table.table_id import TableId
from application.domain.service.match_discovery_rule import match_discovery_rule
from application.exceptions import NotFoundError
from application.port.inbound.table.reset_table_selection import (
    ResetTableSelectionUseCase,
    ResetTableSelectionUseCaseInput,
    ResetTableSelectionUseCaseOutput,
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

    from application.port.outbound.discovery_rule.discovery_rules_repo import (
        DiscoveryRulesRepo,
    )
    from application.port.outbound.table.tables_repo import (
        TablesRepo,
    )
    from application.port.outbound.table_maintenance_preset.table_maintenance_presets_repo import (
        TableMaintenancePresetsRepo,
    )
    from application.port.outbound.workflow.send_table_signal import (
        SendTableSignalGateway,
    )


class ResetTableSelectionService(ResetTableSelectionUseCase):
    """Hand a table back to discovery rules and apply the current decision."""

    def __init__(  # noqa: PLR0913
        self,
        tables_repo: TablesRepo,
        rules_repo: DiscoveryRulesRepo,
        presets_repo: TableMaintenancePresetsRepo,
        signal_gateway: SendTableSignalGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repos, the signal gateway and the clock."""
        self._tables_repo = tables_repo
        self._rules_repo = rules_repo
        self._presets_repo = presets_repo
        self._signal_gateway = signal_gateway
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
            rule = match_discovery_rule(self._rules_repo.list_all(), table.name)
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
        self._signal_gateway.send(
            SendTableSignalGatewayInput(
                table_uuid=table.id.value,
                table_name=table.name.fully_qualified(),
                signal=SIGNAL_RESUME if table.needs_reconcile_workflow else SIGNAL_STOP,
                start_if_missing=table.needs_reconcile_workflow,
            )
        )
        return ResetTableSelectionUseCaseOutput(**table_output_fields(table))
