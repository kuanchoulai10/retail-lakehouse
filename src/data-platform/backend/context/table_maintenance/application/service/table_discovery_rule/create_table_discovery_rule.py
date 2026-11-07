"""Define the CreateTableDiscoveryRuleService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from context.table_maintenance.application.domain.model.table_discovery_rule import (
    RuleEffect,
    TableDiscoveryRule,
    TableDiscoveryRuleId,
    TablePattern,
)
from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePresetId,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_discovery_rule import (
    CreateTableDiscoveryRuleUseCase,
    CreateTableDiscoveryRuleUseCaseInput,
    CreateTableDiscoveryRuleUseCaseOutput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors
from context.table_maintenance.application.service.table_discovery_rule.table_discovery_rule_output_fields import (
    table_discovery_rule_output_fields,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.table_discovery_rule import (
        TableDiscoveryRulesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_preset import (
        TableMaintenancePresetsRepo,
    )


class CreateTableDiscoveryRuleService(CreateTableDiscoveryRuleUseCase):
    """Create a discovery rule that points at an existing preset."""

    def __init__(
        self,
        rules_repo: TableDiscoveryRulesRepo,
        presets_repo: TableMaintenancePresetsRepo,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        new_id: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        """Bind the repos, the clock and the id generator."""
        self._rules_repo = rules_repo
        self._presets_repo = presets_repo
        self._clock = clock
        self._new_id = new_id

    def execute(self, request: CreateTableDiscoveryRuleUseCaseInput) -> CreateTableDiscoveryRuleUseCaseOutput:
        """Create the rule after checking its preset exists."""
        with translate_domain_errors():
            effect = RuleEffect(request.effect)
            preset_id = None if request.preset_id is None else TableMaintenancePresetId(request.preset_id)
            if preset_id is not None and self._presets_repo.get(preset_id) is None:
                raise NotFoundError(f"table maintenance preset {preset_id} not found")
            rule = TableDiscoveryRule.create(
                TableDiscoveryRuleId(self._new_id()),
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
            self._rules_repo.create(rule)
        return CreateTableDiscoveryRuleUseCaseOutput(**table_discovery_rule_output_fields(rule))
