"""Define the match_table_discovery_rule domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from context.table_maintenance.application.domain.model.table import TableName
    from context.table_maintenance.application.domain.model.table_discovery_rule import (
        TableDiscoveryRule,
    )


def match_table_discovery_rule(rules: Sequence[TableDiscoveryRule], name: TableName) -> TableDiscoveryRule | None:
    """Return the first enabled rule matching the table.

    Rules are ordered by priority ascending, ties broken by rule id.
    """
    ordered = sorted(rules, key=lambda rule: (rule.priority, rule.id.value))
    for rule in ordered:
        if rule.enabled and rule.pattern.matches(name):
            return rule
    return None
