"""Define the match_table_discovery_rule domain service."""

from __future__ import annotations

from collections.abc import Sequence

from application.domain.model.table_discovery_rule import TableDiscoveryRule
from application.domain.model.table import TableName


def match_table_discovery_rule(
    rules: Sequence[TableDiscoveryRule], name: TableName
) -> TableDiscoveryRule | None:
    """Return the first enabled rule matching the table.

    Rules are ordered by priority ascending, ties broken by rule id.
    """
    ordered = sorted(rules, key=lambda rule: (rule.priority, rule.id.value))
    for rule in ordered:
        if rule.enabled and rule.pattern.matches(name):
            return rule
    return None
