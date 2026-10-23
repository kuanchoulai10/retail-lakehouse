"""Define the match_discovery_rule domain service."""

from __future__ import annotations

from collections.abc import Sequence

from application.domain.model.discovery_rule.discovery_rule import DiscoveryRule
from application.domain.model.managed_table.table_name import TableName


def match_discovery_rule(
    rules: Sequence[DiscoveryRule], name: TableName
) -> DiscoveryRule | None:
    """Return the first enabled rule matching the table.

    Rules are ordered by priority ascending, ties broken by rule id.
    """
    ordered = sorted(rules, key=lambda rule: (rule.priority, rule.id.value))
    for rule in ordered:
        if rule.enabled and rule.pattern.matches(name):
            return rule
    return None
