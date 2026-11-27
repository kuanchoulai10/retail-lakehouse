"""Test decide_table_management: a management decision says whether a known table is managed, and what decided it."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context.table_maintenance.application.domain.model.shared import TableId
from context.table_maintenance.application.domain.model.table import (
    InvalidTableTransition,
    Table,
    TableManagementChange,
    TableName,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_discovery_policy import DecidedBy, ManagementDecision
from context.table_maintenance.application.domain.service.table import decide_table_management
from tests.context.table_maintenance.discovery_decision_samples import MANAGED, SAMPLE_POLICY_ID, UNMANAGED

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
NAME = TableName(catalog="iceberg", namespace="sales", table="orders")


def _decision(manage: bool, *, version: int = 1, position: int | None = None) -> ManagementDecision:
    return ManagementDecision(
        manage=manage,
        decided_by=DecidedBy(policy_id=SAMPLE_POLICY_ID, policy_version=version, rule_position=position),
    )


def _managed() -> Table:
    return Table.register(TableId("u"), NAME, MANAGED, T0)


def test_an_unmanaging_decision_unmanages_a_managed_table():
    """A managed table an unmanaging decision now decides becomes unmanaged, recording that decision."""
    t = _managed()
    assert decide_table_management(t, UNMANAGED, T1) == TableManagementChange.UNMANAGED
    assert (t.status, t.decided_by) == (TableStatus.UNMANAGED, UNMANAGED.decided_by)


def test_nothing_attached_unmanages_a_managed_table_and_names_no_policy():
    """A managed table no policy applies to any more is unmanaged, decided by nothing."""
    t = _managed()
    assert decide_table_management(t, ManagementDecision.nothing_attached(), T1) == TableManagementChange.UNMANAGED
    assert (t.status, t.decided_by) == (TableStatus.UNMANAGED, None)


def test_a_managing_decision_manages_an_unmanaged_table_again():
    """An unmanaged table a managing decision now decides is managed again under that decision."""
    t = _managed()
    t.unmanage(UNMANAGED.decided_by, T0)
    again = _decision(True, position=2)
    assert decide_table_management(t, again, T1) == TableManagementChange.MANAGED
    assert (t.status, t.decided_by) == (TableStatus.MANAGED, again.decided_by)


def test_an_equal_decision_is_unchanged():
    """A managed table still managed, or an unmanaged one still unmanaged, by an equal decision is unchanged."""
    t = _managed()
    assert decide_table_management(t, MANAGED, T1) == TableManagementChange.UNCHANGED
    assert t.updated_at == T0
    t.unmanage(UNMANAGED.decided_by, T1)
    assert decide_table_management(t, UNMANAGED, T1) == TableManagementChange.UNCHANGED


def test_a_dropped_table_cannot_be_decided():
    """A dropped table is never decided again."""
    t = _managed()
    t.mark_dropped(T1)
    with pytest.raises(InvalidTableTransition):
        decide_table_management(t, UNMANAGED, T1)


def test_another_rule_managing_a_managed_table_is_a_decision_change():
    """A managed table now managed by another rule stays managed and reports the decision change."""
    t = _managed()
    other = _decision(True, position=2)
    assert decide_table_management(t, other, T1) == TableManagementChange.DECISION_CHANGED
    assert (t.status, t.decided_by) == (TableStatus.MANAGED, other.decided_by)


def test_a_new_version_managing_a_managed_table_is_a_decision_change():
    """The same rule in a new version of the policy moves the decision: management is the same, the version is not."""
    t = _managed()
    newer = _decision(True, version=2, position=1)
    assert decide_table_management(t, newer, T1) == TableManagementChange.DECISION_CHANGED
    assert t.decided_by == newer.decided_by


def test_another_decider_unmanaging_an_unmanaged_table_is_a_decision_change():
    """An unmanaged table another rule now leaves unmanaged stays unmanaged and reports the decision change."""
    t = Table.register(TableId("u"), NAME, UNMANAGED, T0)
    other = _decision(False, position=2)
    assert decide_table_management(t, other, T1) == TableManagementChange.DECISION_CHANGED
    assert (t.status, t.decided_by) == (TableStatus.UNMANAGED, other.decided_by)


def test_an_unmanaged_table_losing_its_policy_is_a_decision_change():
    """An unmanaged table no policy applies to any more stays unmanaged, and now names no policy."""
    t = Table.register(TableId("u"), NAME, UNMANAGED, T0)
    assert (
        decide_table_management(t, ManagementDecision.nothing_attached(), T1) == TableManagementChange.DECISION_CHANGED
    )
    assert (t.status, t.decided_by) == (TableStatus.UNMANAGED, None)


def test_an_undecided_table_no_policy_decides_becomes_unmanaged_and_reports_the_decision():
    """Nothing deciding an undecided table unmanages it; the status moved, so the change is saved."""
    t = Table.register_undecided(TableId("u"), NAME, T0)

    change = decide_table_management(t, ManagementDecision.nothing_attached(), T1)

    assert change == TableManagementChange.DECISION_CHANGED
    assert (t.status, t.decided_by, t.updated_at) == (TableStatus.UNMANAGED, None, T1)


def test_an_undecided_table_an_unmanaging_decision_decides_reports_the_decision():
    """An undecided table an exclude decides is unmanaged and saved; there is no workflow to stop."""
    t = Table.register_undecided(TableId("u"), NAME, T0)

    assert decide_table_management(t, UNMANAGED, T1) == TableManagementChange.DECISION_CHANGED
    assert (t.status, t.decided_by) == (TableStatus.UNMANAGED, UNMANAGED.decided_by)


def test_an_undecided_table_a_managing_decision_decides_is_managed():
    """An undecided table an include decides becomes managed, so its workflow is started."""
    t = Table.register_undecided(TableId("u"), NAME, T0)

    assert decide_table_management(t, MANAGED, T1) == TableManagementChange.MANAGED
    assert t.status == TableStatus.MANAGED
