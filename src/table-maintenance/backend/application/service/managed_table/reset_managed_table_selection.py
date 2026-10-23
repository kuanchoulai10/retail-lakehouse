"""Define the ResetManagedTableSelectionService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.maintenance.workflow_ids import (
    SIGNAL_RESUME,
    SIGNAL_STOP,
)
from application.domain.model.managed_table.table_uuid import TableUuid
from application.domain.service.match_discovery_rule import match_discovery_rule
from application.exceptions import NotFoundError
from application.port.inbound.managed_table.reset_managed_table_selection import (
    ResetManagedTableSelectionUseCase,
    ResetManagedTableSelectionUseCaseInput,
    ResetManagedTableSelectionUseCaseOutput,
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

    from application.port.outbound.discovery_rule.discovery_rules_repo import (
        DiscoveryRulesRepo,
    )
    from application.port.outbound.managed_table.managed_tables_repo import (
        ManagedTablesRepo,
    )
    from application.port.outbound.policy_template.policy_templates_repo import (
        PolicyTemplatesRepo,
    )
    from application.port.outbound.workflow.send_table_signal import (
        SendTableSignalGateway,
    )


class ResetManagedTableSelectionService(ResetManagedTableSelectionUseCase):
    """Hand a table back to discovery rules and apply the current decision."""

    def __init__(  # noqa: PLR0913
        self,
        tables_repo: ManagedTablesRepo,
        rules_repo: DiscoveryRulesRepo,
        templates_repo: PolicyTemplatesRepo,
        signal_gateway: SendTableSignalGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repos, the signal gateway and the clock."""
        self._tables_repo = tables_repo
        self._rules_repo = rules_repo
        self._templates_repo = templates_repo
        self._signal_gateway = signal_gateway
        self._clock = clock

    def execute(
        self, request: ResetManagedTableSelectionUseCaseInput
    ) -> ResetManagedTableSelectionUseCaseOutput:
        """Re-run rule matching for the table, whether or not discovery is enabled."""
        table = self._tables_repo.get(TableUuid(request.uuid))
        if table is None:
            raise NotFoundError(f"managed table {request.uuid} not found")
        now = self._clock()
        with translate_domain_errors():
            table.reset_to_auto(now)
            rule = match_discovery_rule(self._rules_repo.list_all(), table.name)
            if rule is None:
                table.apply_auto_decision(None, None, None, now)
            elif rule.template_id is None:
                table.apply_auto_decision(rule.id, None, None, now)
            else:
                template = self._templates_repo.get(rule.template_id)
                if template is None:
                    raise NotFoundError(
                        f"policy template {rule.template_id} of rule {rule.id} "
                        "not found"
                    )
                table.apply_auto_decision(rule.id, template.id, template.settings, now)
            self._tables_repo.update(table)
        self._signal_gateway.send(
            SendTableSignalGatewayInput(
                table_uuid=table.id.value,
                signal=SIGNAL_RESUME if table.needs_reconcile_workflow else SIGNAL_STOP,
                start_if_missing=table.needs_reconcile_workflow,
            )
        )
        return ResetManagedTableSelectionUseCaseOutput(
            **managed_table_output_fields(table)
        )
