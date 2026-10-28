"""Define the UpdateDiscoveryRuleService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.discovery_rule.discovery_rule_id import DiscoveryRuleId
from application.domain.model.discovery_rule.rule_effect import RuleEffect
from application.domain.model.discovery_rule.table_pattern import TablePattern
from application.domain.model.table_maintenance_preset.table_maintenance_preset_id import (
    TableMaintenancePresetId,
)
from application.exceptions import NotFoundError
from application.port.inbound.discovery_rule.update_discovery_rule import (
    UpdateDiscoveryRuleUseCase,
    UpdateDiscoveryRuleUseCaseInput,
    UpdateDiscoveryRuleUseCaseOutput,
)
from application.service.discovery_rule.discovery_rule_output_fields import (
    discovery_rule_output_fields,
)
from application.service.translate_domain_errors import translate_domain_errors

if TYPE_CHECKING:
    from collections.abc import Callable

    from application.port.outbound.discovery_rule.discovery_rules_repo import (
        DiscoveryRulesRepo,
    )
    from application.port.outbound.table_maintenance_preset.table_maintenance_presets_repo import (
        TableMaintenancePresetsRepo,
    )


class UpdateDiscoveryRuleService(UpdateDiscoveryRuleUseCase):
    """Replace a discovery rule's definition."""

    def __init__(
        self,
        rules_repo: DiscoveryRulesRepo,
        presets_repo: TableMaintenancePresetsRepo,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repos and the clock."""
        self._rules_repo = rules_repo
        self._presets_repo = presets_repo
        self._clock = clock

    def execute(
        self, request: UpdateDiscoveryRuleUseCaseInput
    ) -> UpdateDiscoveryRuleUseCaseOutput:
        """Replace the rule; the rule is left unchanged when the request is invalid."""
        rule = self._rules_repo.get(DiscoveryRuleId(request.id))
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
        return UpdateDiscoveryRuleUseCaseOutput(**discovery_rule_output_fields(rule))
