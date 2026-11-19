"""Test the TableDiscoveryRules aggregate: matching, first-match decision, whole-list replacement."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context.table_maintenance.application.domain.model.table import TableName
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    GLOBAL_TABLE_DISCOVERY_RULES_ID,
    GlobList,
    RuleAction,
    StaleDiscoveryRulesVersion,
    TableDiscoveryRule,
    TableDiscoveryRuleId,
    TableDiscoveryRules,
    UnknownDiscoveryRuleId,
)

RULE_1 = "dr-00000000000000000000000001"
RULE_IN = "dr-00000000000000000000000002"
RULE_EX = "dr-00000000000000000000000003"
RULE_OFF = "dr-00000000000000000000000004"
RULE_A = "dr-00000000000000000000000005"
RULE_B = "dr-00000000000000000000000006"
RULE_SAME = "dr-00000000000000000000000007"
RULE_EDITED = "dr-00000000000000000000000008"
RULE_NEW = "dr-00000000000000000000000009"
UNKNOWN_RULE = "dr-00000000000000000000000010"
T0 = datetime(2026, 11, 1, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)


def _rule(  # noqa: PLR0913
    rid: str,
    priority: int,
    action: RuleAction = RuleAction.INCLUDE,
    *,
    enabled: bool = True,
    catalogs: tuple[str, ...] = ("*",),
    namespaces: tuple[str, ...] = ("*",),
    tables: tuple[str, ...] = ("*",),
    now: datetime = T0,
) -> TableDiscoveryRule:
    return TableDiscoveryRule.create(
        id=TableDiscoveryRuleId(rid),
        priority=priority,
        action=action,
        enabled=enabled,
        catalogs=GlobList(globs=catalogs),
        namespaces=GlobList(globs=namespaces),
        tables=GlobList(globs=tables),
        now=now,
    )


def _name(catalog: str = "iceberg", namespace: str = "sales", table: str = "orders") -> TableName:
    return TableName(catalog=catalog, namespace=namespace, table=table)


def _decided(rules: TableDiscoveryRules, name: TableName) -> str | None:
    rule = rules.decide(name)
    return None if rule is None else rule.id.value


def _rules(*rules: TableDiscoveryRule) -> TableDiscoveryRules:
    aggregate = TableDiscoveryRules.empty()
    aggregate.replace(rules, 0, T0, new_ids={rule.id for rule in rules})
    return aggregate


def test_any_glob_in_field_matches_and_all_fields_must_match():
    """A rule matches when any glob of each field matches and all three fields match."""
    rule = _rule(RULE_1, 1, catalogs=("iceberg", "lake"), namespaces=("hr", "sal*"), tables=("tmp_*", "orders"))
    assert rule.matches(_name())
    assert rule.matches(_name(catalog="lake", namespace="hr", table="tmp_x"))
    assert not rule.matches(_name(catalog="other"))
    assert not rule.matches(_name(namespace="finance"))
    assert not rule.matches(_name(table="customers"))


def test_matching_is_case_sensitive():
    """Globs match case-sensitively."""
    assert not _rule(RULE_1, 1, tables=("Orders",)).matches(_name())


def test_namespace_glob_matches_full_dotted_name():
    """A namespace glob is matched on the full dotted namespace name."""
    rule = _rule(RULE_1, 1, namespaces=("prod.*",))
    assert rule.matches(_name(namespace="prod.sales"))
    assert rule.matches(_name(namespace="prod.sales.eu"))
    assert not rule.matches(_name(namespace="prod"))


def test_glob_list_must_not_be_empty():
    """A field holds at least one glob, and no glob is empty."""
    with pytest.raises(ValueError, match="at least one glob"):
        GlobList(globs=())
    with pytest.raises(ValueError, match="empty"):
        GlobList(globs=("",))


def test_decide_returns_first_enabled_match_by_priority():
    """The enabled matching rule with the lowest priority decides."""
    rules = _rules(
        _rule(RULE_IN, 20),
        _rule(RULE_EX, 10, RuleAction.EXCLUDE, tables=("orders",)),
    )
    assert _decided(rules, _name()) == RULE_EX
    assert _decided(rules, _name(table="customers")) == RULE_IN


def test_disabled_rule_skipped():
    """A disabled rule is skipped as if absent."""
    rules = _rules(_rule(RULE_OFF, 1, RuleAction.EXCLUDE, enabled=False), _rule(RULE_IN, 2))
    assert _decided(rules, _name()) == RULE_IN
    assert _rules(_rule(RULE_OFF, 1, enabled=False)).decide(_name()) is None


def test_no_rule_decides_nothing():
    """An empty list decides no table."""
    assert TableDiscoveryRules.empty().decide(_name()) is None


def test_empty_list_is_the_global_singleton_at_version_zero():
    """The rules start empty at version 0 under the singleton id."""
    rules = TableDiscoveryRules.empty()
    assert (rules.id, rules.rules, rules.version) == (GLOBAL_TABLE_DISCOVERY_RULES_ID, (), 0)


def test_global_rules_id_is_the_fixed_dp_id():
    """The one rule list has the fixed id of the dp prefix whose suffix is all zeros."""
    assert GLOBAL_TABLE_DISCOVERY_RULES_ID.value == "dp-00000000000000000000000000"


def test_replace_orders_by_priority_and_bumps_version():
    """A replacement stores the rules in priority order as the next version."""
    rules = _rules(_rule(RULE_B, 20), _rule(RULE_A, 10))
    assert [r.id.value for r in rules.rules] == [RULE_A, RULE_B]
    assert rules.version == 1


def test_equal_priorities_rejected_and_list_unchanged():
    """Two rules with one priority are rejected; the list stays as it was."""
    rules = _rules(_rule(RULE_A, 10))
    with pytest.raises(ValueError, match="priority 5"):
        rules.replace((_rule(RULE_A, 5), _rule(RULE_B, 5)), 1, T1, new_ids={TableDiscoveryRuleId(RULE_B)})
    assert ([r.id.value for r in rules.rules], rules.rules[0].priority, rules.version) == ([RULE_A], 10, 1)


def test_duplicate_rule_ids_rejected():
    """Two rules with one id are rejected."""
    with pytest.raises(ValueError, match=f"rule {RULE_A}"):
        _rules(_rule(RULE_A, 1), _rule(RULE_A, 2))


def test_stale_version_rejected_and_list_unchanged():
    """A replacement from a version that is not the current one is rejected."""
    rules = _rules(_rule(RULE_A, 10))
    with pytest.raises(StaleDiscoveryRulesVersion, match="version 1, not 0"):
        rules.replace((), 0, T1)
    assert (len(rules.rules), rules.version) == (1, 1)


def test_replace_keeps_created_at_and_touches_only_changed_rules():
    """A kept rule keeps its creation time; only a changed one gets a new update time."""
    rules = _rules(_rule(RULE_SAME, 1), _rule(RULE_EDITED, 2))
    rules.replace(
        (_rule(RULE_SAME, 1, now=T1), _rule(RULE_EDITED, 2, RuleAction.EXCLUDE, now=T1), _rule(RULE_NEW, 3, now=T1)),
        1,
        T1,
        new_ids={TableDiscoveryRuleId(RULE_NEW)},
    )
    by_id = {r.id.value: r for r in rules.rules}
    assert (by_id[RULE_SAME].created_at, by_id[RULE_SAME].updated_at) == (T0, T0)
    assert (by_id[RULE_EDITED].created_at, by_id[RULE_EDITED].updated_at, by_id[RULE_EDITED].action) == (
        T0,
        T1,
        RuleAction.EXCLUDE,
    )
    assert (by_id[RULE_NEW].created_at, by_id[RULE_NEW].updated_at) == (T1, T1)
    assert rules.version == 2


def test_replace_with_empty_list_removes_every_rule():
    """Replacing with no rules deletes them all."""
    rules = _rules(_rule(RULE_A, 1))
    rules.replace((), 1, T1)
    assert (rules.rules, rules.version) == ((), 2)


def test_an_id_neither_stored_nor_new_is_rejected_and_list_unchanged():
    """A rule must either be in the list already or be declared new; a made-up id is rejected."""
    rules = _rules(_rule(RULE_A, 1))
    with pytest.raises(UnknownDiscoveryRuleId, match=f"unknown discovery rule id {UNKNOWN_RULE}"):
        rules.replace((_rule(RULE_A, 1), _rule(UNKNOWN_RULE, 2)), 1, T1)
    assert ([r.id.value for r in rules.rules], rules.version) == ([RULE_A], 1)


def test_unknown_discovery_rule_id_is_a_value_error():
    """A made-up id is an invalid request, not a conflict."""
    assert issubclass(UnknownDiscoveryRuleId, ValueError)
    assert not issubclass(UnknownDiscoveryRuleId, StaleDiscoveryRulesVersion)
