"""Define the TableDiscoveryRule aggregate root."""

from __future__ import annotations

from datetime import datetime

from pydantic import model_validator

from base import AggregateRoot
from context.table_maintenance.application.domain.model.table_discovery_rule.rule_effect import (
    RuleEffect,
)
from context.table_maintenance.application.domain.model.table_discovery_rule.table_discovery_rule_id import (
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.domain.model.table_discovery_rule.table_pattern import (
    TablePattern,
)
from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePresetId,
)


def _validate(effect: RuleEffect, preset_id: TableMaintenancePresetId | None) -> None:
    if effect == RuleEffect.INCLUDE and preset_id is None:
        raise ValueError("an include rule requires a preset")
    if effect == RuleEffect.EXCLUDE and preset_id is not None:
        raise ValueError("an exclude rule must not have a preset")


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

    @model_validator(mode="after")
    def _effect_and_preset_agree(self) -> TableDiscoveryRule:
        _validate(self.effect, self.preset_id)
        return self

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
        """Replace the rule's definition, leaving it unchanged if invalid.

        An invalid effect and preset pair raises a plain ValueError and a
        wrong type raises ValidationError; both answer 422.
        """
        _validate(effect, preset_id)
        self._assign_together(
            priority=priority,
            effect=effect,
            pattern=pattern,
            preset_id=preset_id,
            enabled=enabled,
            updated_at=now,
        )
