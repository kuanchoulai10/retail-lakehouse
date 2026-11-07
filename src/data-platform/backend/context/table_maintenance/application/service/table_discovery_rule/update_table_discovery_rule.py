"""Define the UpdateTableDiscoveryRuleService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_discovery_rule import (
    TableDiscoveryRuleId,
    RuleEffect,
    TablePattern,
)
from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePresetId,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_discovery_rule import (
    UpdateTableDiscoveryRuleUseCase,
    UpdateTableDiscoveryRuleUseCaseInput,
    UpdateTableDiscoveryRuleUseCaseOutput,
)
from context.table_maintenance.application.service.table_discovery_rule.table_discovery_rule_output_fields import (
    table_discovery_rule_output_fields,
)
from context.table_maintenance.application.service.shared import translate_domain_errors

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.table_discovery_rule import (
        TableDiscoveryRulesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_preset import (
        TableMaintenancePresetsRepo,
    )


class UpdateTableDiscoveryRuleService(UpdateTableDiscoveryRuleUseCase):
    """Replace a discovery rule's definition."""

    def __init__(
        self,
        rules_repo: TableDiscoveryRulesRepo,
        presets_repo: TableMaintenancePresetsRepo,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repos and the clock."""
        self._rules_repo = rules_repo
        self._presets_repo = presets_repo
        self._clock = clock

    def execute(
        self, request: UpdateTableDiscoveryRuleUseCaseInput
    ) -> UpdateTableDiscoveryRuleUseCaseOutput:
        """Replace the rule; the rule is left unchanged when the request is invalid."""
        rule = self._rules_repo.get(TableDiscoveryRuleId(request.id))
        if rule is None:
            raise NotFoundError(f"discovery rule {request.id} not found")
        with translate_domain_errors():
            effect = RuleEffect(request.effect)
            preset_id = (
                None
                if request.preset_id is None
                else TableMaintenancePresetId(request.preset_id)
            )
            if preset_id is not None and self._presets_repo.get(preset_id) is None:
                raise NotFoundError(f"table maintenance preset {preset_id} not found")
            rule.update(
                request.priority,
                effect,
                TablePattern(
                    request.catalog_pattern,
                    request.namespace_pattern,
                    request.table_pattern,
                ),
                preset_id,
                request.enabled,
                self._clock(),
            )
            self._rules_repo.update(rule)
        return UpdateTableDiscoveryRuleUseCaseOutput(
            **table_discovery_rule_output_fields(rule)
        )
