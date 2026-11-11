"""Test decide_table_management: the discovery rules decide whether a known table is managed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context.table_maintenance.application.domain.model.table import (
    InvalidTableTransition,
    Table,
    TableId,
    TableManagementChange,
    TableName,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    GlobList,
    RuleAction,
    TableDiscoveryRule,
    TableDiscoveryRuleId,
    TableDiscoveryRules,
)
from context.table_maintenance.application.domain.service.table import decide_table_management

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
NAME = TableName(catalog="iceberg", namespace="sales", table="orders")


def _rule(rid: str, action: RuleAction, priority: int = 10) -> TableDiscoveryRule:
    every = GlobList(globs=("*",))
    return TableDiscoveryRule.create(
        id=TableDiscoveryRuleId(rid),
        priority=priority,
        action=action,
        enabled=True,
        catalogs=every,
        namespaces=every,
        tables=every,
        now=T0,
    )


def _rules(*rules: TableDiscoveryRule) -> TableDiscoveryRules:
    aggregate = TableDiscoveryRules.empty()
    aggregate.replace(rules, 0, T0, new_ids={rule.id for rule in rules})
    return aggregate


def _managed() -> Table:
    return Table.register(TableId("u"), NAME, TableDiscoveryRuleId("r-in"), T0)


def test_an_exclude_match_unmanages_a_managed_table():
    """A managed table that an exclude rule now decides becomes unmanaged."""
    t = _managed()
    assert decide_table_management(t, _rules(_rule("r-ex", RuleAction.EXCLUDE)), T1) == TableManagementChange.UNMANAGED
    assert t.status == TableStatus.UNMANAGED


def test_no_match_unmanages_a_managed_table():
    """A managed table no rule matches becomes unmanaged."""
    t = _managed()
    assert decide_table_management(t, _rules(), T1) == TableManagementChange.UNMANAGED


def test_an_include_match_manages_an_unmanaged_table_again():
    """An unmanaged table an include rule now decides is managed again under that rule."""
    t = _managed()
    t.unmanage(T0)
    assert decide_table_management(t, _rules(_rule("r-2", RuleAction.INCLUDE)), T1) == TableManagementChange.MANAGED
    assert (t.status, t.matched_rule_id) == (TableStatus.MANAGED, TableDiscoveryRuleId("r-2"))


def test_a_decision_that_keeps_the_status_is_unchanged():
    """A managed table still included, or an unmanaged one still excluded, is unchanged."""
    t = _managed()
    assert decide_table_management(t, _rules(_rule("r-in", RuleAction.INCLUDE)), T1) == TableManagementChange.UNCHANGED
    t.unmanage(T1)
    assert decide_table_management(t, _rules(_rule("r-ex", RuleAction.EXCLUDE)), T1) == TableManagementChange.UNCHANGED


def test_the_first_enabled_matching_rule_decides():
    """Rules apply in priority order; the first match decides."""
    t = _managed()
    rules = _rules(_rule("r-in", RuleAction.INCLUDE, priority=20), _rule("r-ex", RuleAction.EXCLUDE, priority=10))
    assert decide_table_management(t, rules, T1) == TableManagementChange.UNMANAGED


def test_a_dropped_table_cannot_be_decided():
    """A dropped table is never decided again."""
    t = _managed()
    t.mark_dropped(T1)
    with pytest.raises(InvalidTableTransition):
        decide_table_management(t, _rules(), T1)


def test_another_include_rule_deciding_a_managed_table_is_a_rule_change():
    """A managed table now decided by another include rule stays managed and reports the rule change."""
    t = _managed()
    assert (
        decide_table_management(t, _rules(_rule("r-2", RuleAction.INCLUDE)), T1) == TableManagementChange.RULE_CHANGED
    )
    assert (t.status, t.matched_rule_id) == (TableStatus.MANAGED, TableDiscoveryRuleId("r-2"))
