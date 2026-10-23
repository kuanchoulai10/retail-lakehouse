from __future__ import annotations

from datetime import UTC, datetime

from application.domain.model.discovery_rule import (
    DiscoveryRule,
    DiscoveryRuleId,
    RuleEffect,
    TablePattern,
)
from application.domain.model.managed_table import TableName
from application.domain.model.policy_template import PolicyTemplateId
from application.domain.service.match_discovery_rule import match_discovery_rule

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def rule(rid, priority, effect, pattern, enabled=True) -> DiscoveryRule:
    return DiscoveryRule.create(
        id=DiscoveryRuleId(rid),
        priority=priority,
        effect=effect,
        pattern=pattern,
        template_id=PolicyTemplateId("t") if effect == RuleEffect.INCLUDE else None,
        enabled=enabled,
        now=NOW,
    )


def test_first_matching_rule_by_priority_wins():
    exclude = rule("a", 10, RuleEffect.EXCLUDE, TablePattern(table="tmp_*"))
    include = rule("b", 20, RuleEffect.INCLUDE, TablePattern())
    rules = [include, exclude]
    assert match_discovery_rule(rules, TableName("c", "n", "tmp_x")) is exclude
    assert match_discovery_rule(rules, TableName("c", "n", "orders")) is include


def test_disabled_rules_are_ignored():
    off = rule("a", 1, RuleEffect.EXCLUDE, TablePattern(), enabled=False)
    on = rule("b", 2, RuleEffect.INCLUDE, TablePattern())
    assert match_discovery_rule([off, on], TableName("c", "n", "t")) is on


def test_no_rules_returns_none():
    assert match_discovery_rule([], TableName("c", "n", "t")) is None


def test_no_match_returns_none():
    r = rule("a", 1, RuleEffect.INCLUDE, TablePattern(catalog="x"))
    assert match_discovery_rule([r], TableName("c", "n", "t")) is None


def test_equal_priority_tie_broken_by_rule_id():
    b = rule("b", 5, RuleEffect.INCLUDE, TablePattern())
    a = rule("a", 5, RuleEffect.EXCLUDE, TablePattern())
    assert match_discovery_rule([b, a], TableName("c", "n", "t")) is a
