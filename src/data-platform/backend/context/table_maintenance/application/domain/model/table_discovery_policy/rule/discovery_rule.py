"""Define the DiscoveryRule value object."""

from __future__ import annotations

from base import ValueObject
from context.table_maintenance.application.domain.model.table_discovery_policy.rule.rule_action import RuleAction
from context.table_maintenance.application.domain.model.table_discovery_policy.rule.table_name_pattern import (
    TableNamePattern,
)


class DiscoveryRule(ValueObject):
    """One rule of a discovery policy: include or exclude the tables whose name matches the pattern."""

    action: RuleAction
    table_name_pattern: TableNamePattern

    def matches(self, table: str) -> bool:
        """Return whether the table name matches the rule's pattern, whatever its action."""
        return self.table_name_pattern.matches(table)
