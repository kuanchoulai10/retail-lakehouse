"""Define the DiscoveryRules value object."""

from __future__ import annotations

from pydantic import field_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.table_discovery_policy.rule.discovery_rule import DiscoveryRule
from context.table_maintenance.application.domain.model.table_discovery_policy.rule.rule_action import RuleAction


class DiscoveryRules(ValueObject):
    """The ordered rules of a discovery policy; the last rule that matches a table decides it.

    A policy needs at least one rule, and may hold exclude rules only. A table that no rule matches is
    not managed. Positions count from 1.
    """

    rules: tuple[DiscoveryRule, ...]

    @field_validator("rules")
    @classmethod
    def _at_least_one(cls, rules: tuple[DiscoveryRule, ...]) -> tuple[DiscoveryRule, ...]:
        if not rules:
            raise ValueError("a discovery policy needs at least one rule")
        return rules

    def deciding_position(self, table: str) -> int | None:
        """Return the 1-based position of the last rule that matches the table, or None when none does."""
        for position in range(len(self.rules), 0, -1):
            if self.rules[position - 1].matches(table):
                return position
        return None

    def manages(self, table: str) -> tuple[bool, int | None]:
        """Return whether the table is managed and the position of the rule that decided it.

        The table is managed when its last matching rule is an include; the position is None when no rule matches.
        """
        position = self.deciding_position(table)
        if position is None:
            return False, None
        return self.rules[position - 1].action is RuleAction.INCLUDE, position
