"""Test decide_table_management: a discovery decision says whether a known table is managed, and what decided it."""

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
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DiscoveryDecision,
    DiscoveryMatch,
    DiscoveryOutcome,
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.domain.service.table import decide_table_management
from tests.context.table_maintenance.discovery_decision_samples import MANAGED, SAMPLE_POLICY_ID, UNMANAGED

RULE_2 = TableDiscoveryRuleId("dr-00000000000000000000000002")
T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
NAME = TableName(catalog="iceberg", namespace="sales", table="orders")


def _decision(outcome: DiscoveryOutcome, *, version: int = 1, rule_id: TableDiscoveryRuleId | None = None):
    return DiscoveryDecision(
        outcome=outcome,
        match=DiscoveryMatch(policy_id=SAMPLE_POLICY_ID, policy_version=version, rule_id=rule_id),
    )


def _managed() -> Table:
    return Table.register(TableId("u"), NAME, MANAGED, T0)


def test_an_unmanaging_decision_unmanages_a_managed_table():
    """A managed table an unmanaging decision now decides becomes unmanaged, recording that decision."""
    t = _managed()
    assert decide_table_management(t, UNMANAGED, T1) == TableManagementChange.UNMANAGED
    assert (t.status, t.discovered_by) == (TableStatus.UNMANAGED, UNMANAGED.match)


def test_a_managing_decision_manages_an_unmanaged_table_again():
    """An unmanaged table a managing decision now decides is managed again under that match."""
    t = _managed()
    t.unmanage(UNMANAGED.match, T0)
    again = _decision(DiscoveryOutcome.MANAGE, rule_id=RULE_2)
    assert decide_table_management(t, again, T1) == TableManagementChange.MANAGED
    assert (t.status, t.discovered_by) == (TableStatus.MANAGED, again.match)


def test_an_equal_decision_is_unchanged():
    """A managed table still managed, or an unmanaged one still unmanaged, by an equal match is unchanged."""
    t = _managed()
    assert decide_table_management(t, MANAGED, T1) == TableManagementChange.UNCHANGED
    assert t.updated_at == T0
    t.unmanage(UNMANAGED.match, T1)
    assert decide_table_management(t, UNMANAGED, T1) == TableManagementChange.UNCHANGED


def test_a_dropped_table_cannot_be_decided():
    """A dropped table is never decided again."""
    t = _managed()
    t.mark_dropped(T1)
    with pytest.raises(InvalidTableTransition):
        decide_table_management(t, UNMANAGED, T1)


def test_another_rule_managing_a_managed_table_is_a_match_change():
    """A managed table now managed by another rule stays managed and reports the match change."""
    t = _managed()
    other = _decision(DiscoveryOutcome.MANAGE, rule_id=RULE_2)
    assert decide_table_management(t, other, T1) == TableManagementChange.MATCH_CHANGED
    assert (t.status, t.discovered_by) == (TableStatus.MANAGED, other.match)


def test_a_new_version_managing_a_managed_table_is_a_match_change():
    """The same rule in a new version of the policy moves the match: management is the same, the version is not."""
    t = _managed()
    newer = _decision(DiscoveryOutcome.MANAGE, version=2, rule_id=MANAGED.match.rule_id)
    assert decide_table_management(t, newer, T1) == TableManagementChange.MATCH_CHANGED
    assert t.discovered_by.policy_version == 2


def test_another_match_unmanaging_an_unmanaged_table_is_a_match_change():
    """An unmanaged table another match now unmanages stays unmanaged and reports the match change."""
    t = Table.register(TableId("u"), NAME, UNMANAGED, T0)
    other = _decision(DiscoveryOutcome.UNMANAGE, rule_id=RULE_2)
    assert decide_table_management(t, other, T1) == TableManagementChange.MATCH_CHANGED
    assert (t.status, t.discovered_by) == (TableStatus.UNMANAGED, other.match)
