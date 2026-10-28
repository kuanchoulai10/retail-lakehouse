"""Define the TableDiscoveryRule aggregate root."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from application.domain.model.table_discovery_rule.table_discovery_rule_id import (
    TableDiscoveryRuleId,
)
from application.domain.model.table_discovery_rule.invalid_table_discovery_rule import (
    InvalidTableDiscoveryRule,
)
from application.domain.model.table_discovery_rule.rule_effect import RuleEffect
from application.domain.model.table_discovery_rule.table_pattern import TablePattern
from application.domain.model.table_maintenance_preset.table_maintenance_preset_id import (
    TableMaintenancePresetId,
)
from base.aggregate_root import AggregateRoot


def _validate(effect: RuleEffect, preset_id: TableMaintenancePresetId | None) -> None:
    if effect == RuleEffect.INCLUDE and preset_id is None:
        raise InvalidTableDiscoveryRule("an include rule requires a preset")
    if effect == RuleEffect.EXCLUDE and preset_id is not None:
        raise InvalidTableDiscoveryRule("an exclude rule must not have a preset")


@dataclass(eq=False)
class TableDiscoveryRule(AggregateRoot[TableDiscoveryRuleId]):
    """Decide whether discovered tables matching a pattern are managed."""

    id: TableDiscoveryRuleId
    priority: int
    effect: RuleEffect
    pattern: TablePattern
    preset_id: TableMaintenancePresetId | None
    enabled: bool
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        """Enforce the effect and preset invariant."""
        _validate(self.effect, self.preset_id)

    @classmethod
    def create(
        cls,
        id: TableDiscoveryRuleId,  # noqa: A002
        priority: int,
        effect: RuleEffect,
        pattern: TablePattern,
        preset_id: TableMaintenancePresetId | None,
        enabled: bool,
        now: datetime,
    ) -> TableDiscoveryRule:
        """Create a rule."""
        return cls(
            id=id,
            priority=priority,
            effect=effect,
            pattern=pattern,
            preset_id=preset_id,
            enabled=enabled,
            created_at=now,
            updated_at=now,
        )

    def update(
        self,
        priority: int,
        effect: RuleEffect,
        pattern: TablePattern,
        preset_id: TableMaintenancePresetId | None,
        enabled: bool,
        now: datetime,
    ) -> None:
        """Replace the rule's definition, leaving it unchanged if invalid."""
        _validate(effect, preset_id)
        self.priority = priority
        self.effect = effect
        self.pattern = pattern
        self.preset_id = preset_id
        self.enabled = enabled
        self.updated_at = now
