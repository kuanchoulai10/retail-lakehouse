"""Define the TableDiscoveryRule aggregate root."""

from __future__ import annotations

from datetime import datetime

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


class TableDiscoveryRule(AggregateRoot[TableDiscoveryRuleId]):
    """Decide whether discovered tables matching a pattern are managed."""

    id: TableDiscoveryRuleId
    priority: int
    effect: RuleEffect
    pattern: TablePattern
    enabled: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        id: TableDiscoveryRuleId,  # noqa: A002
        priority: int,
        effect: RuleEffect,
        pattern: TablePattern,
        enabled: bool,
        now: datetime,
    ) -> TableDiscoveryRule:
        """Create a rule."""
        return cls(
            id=id,
            priority=priority,
            effect=effect,
            pattern=pattern,
            enabled=enabled,
            created_at=now,
            updated_at=now,
        )

    def update(
        self,
        priority: int,
        effect: RuleEffect,
        pattern: TablePattern,
        enabled: bool,
        now: datetime,
    ) -> None:
        """Replace the rule's definition, leaving it unchanged if invalid."""
        self._assign_together(
            priority=priority,
            effect=effect,
            pattern=pattern,
            enabled=enabled,
            updated_at=now,
        )
