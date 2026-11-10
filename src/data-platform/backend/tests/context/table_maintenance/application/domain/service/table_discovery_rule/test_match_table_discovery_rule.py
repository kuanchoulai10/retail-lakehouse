"""Test how the discovery rule for a table is chosen from the rules."""

from __future__ import annotations

from datetime import UTC, datetime

from context.table_maintenance.application.domain.model.table import TableName
from context.table_maintenance.application.domain.model.table_discovery_rule import (
    RuleEffect,
    TableDiscoveryRule,
    TableDiscoveryRuleId,
    TablePattern,
)
from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePresetId,
)
from context.table_maintenance.application.domain.service.table_discovery_rule import (
    match_table_discovery_rule,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def rule(rid, priority, effect, pattern, enabled=True) -> TableDiscoveryRule:
    """Build a discovery rule with the given id, priority, effect and pattern."""
    return TableDiscoveryRule.create(
        id=TableDiscoveryRuleId(rid),
        priority=priority,
        effect=effect,
        pattern=pattern,
        preset_id=TableMaintenancePresetId("t") if effect == RuleEffect.INCLUDE else None,
        enabled=enabled,
        now=NOW,
    )


def test_first_matching_rule_by_priority_wins():
    """The matching rule with the best priority is chosen."""
    exclude = rule("a", 10, RuleEffect.EXCLUDE, TablePattern(table="tmp_*"))
    include = rule("b", 20, RuleEffect.INCLUDE, TablePattern())
    rules = [include, exclude]
    assert match_table_discovery_rule(rules, TableName(catalog="c", namespace="n", table="tmp_x")) is exclude
    assert match_table_discovery_rule(rules, TableName(catalog="c", namespace="n", table="orders")) is include


def test_disabled_rules_are_ignored():
    """Disabled rules never match."""
    off = rule("a", 1, RuleEffect.EXCLUDE, TablePattern(), enabled=False)
    on = rule("b", 2, RuleEffect.INCLUDE, TablePattern())
    assert match_table_discovery_rule([off, on], TableName(catalog="c", namespace="n", table="t")) is on


def test_no_rules_returns_none():
    """With no rules nothing matches."""
    assert match_table_discovery_rule([], TableName(catalog="c", namespace="n", table="t")) is None


def test_no_match_returns_none():
    """A table that no pattern matches gets no rule."""
    r = rule("a", 1, RuleEffect.INCLUDE, TablePattern(catalog="x"))
    assert match_table_discovery_rule([r], TableName(catalog="c", namespace="n", table="t")) is None


def test_equal_priority_tie_broken_by_rule_id():
    """Rules of equal priority are ordered by rule id."""
    b = rule("b", 5, RuleEffect.INCLUDE, TablePattern())
    a = rule("a", 5, RuleEffect.EXCLUDE, TablePattern())
    assert match_table_discovery_rule([b, a], TableName(catalog="c", namespace="n", table="t")) is a
