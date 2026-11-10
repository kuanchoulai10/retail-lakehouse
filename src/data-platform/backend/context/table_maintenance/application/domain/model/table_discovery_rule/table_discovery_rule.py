"""Define the TableDiscoveryRule aggregate root."""

from __future__ import annotations

from datetime import datetime

from pydantic import model_validator

from base.model import AggregateRoot
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

        The model validator re-runs on every assignment, so assigning the
        effect and the preset one at a time would fail on the half-changed
        state. The new definition is built and validated as a whole first,
        then taken over in one step.
        """
        _validate(effect, preset_id)
        candidate = TableDiscoveryRule(
            id=self.id,
            priority=priority,
            effect=effect,
            pattern=pattern,
            preset_id=preset_id,
            enabled=enabled,
            created_at=self.created_at,
            updated_at=now,
        )
        self.__dict__.update(candidate.__dict__)
