"""Test the policies a Table holds and the undecided table: one attached before discovery decided it."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.shared import (
    PolicyNotAttached,
    TableDiscoveryPolicyId,
    TableId,
    TableMaintenancePolicyId,
)
from context.table_maintenance.application.domain.model.table import (
    InvalidTableTransition,
    Table,
    TableName,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_discovery_policy import DecidedBy
from tests.context.table_maintenance.discovery_decision_samples import MANAGED, SAMPLE_POLICY_ID

T0 = datetime(2026, 11, 27, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
T2 = T1 + timedelta(hours=1)
NAME = TableName(catalog="iceberg", namespace="sales", table="orders")
SALES = TableDiscoveryPolicyId("dp-00000000000000000000000011")
EVERYTHING = TableDiscoveryPolicyId("dp-00000000000000000000000012")
NIGHTLY = TableMaintenancePolicyId("mp-00000000000000000000000011")
HOURLY = TableMaintenancePolicyId("mp-00000000000000000000000012")
DECIDED_BY = DecidedBy(policy_id=SAMPLE_POLICY_ID, policy_version=1, rule_position=1)


def managed() -> Table:
    """Provide a table discovery registered as managed at T0."""
    return Table.register(TableId("u1"), NAME, MANAGED, T0)


def dropped() -> Table:
    """Provide a managed table dropped at T1."""
    table = managed()
    table.mark_dropped(T1)
    return table


def test_a_registered_table_holds_no_policy():
    """A table discovery registers holds neither a discovery nor a maintenance policy of its own."""
    table = managed()
    assert table.discovery_policy_id is None
    assert table.maintenance_policy_id is None


def test_attach_a_discovery_policy_to_a_table_holding_none():
    """Attaching a discovery policy where none is sets it and moves the update time."""
    table = managed()
    table.attach_discovery_policy(SALES, T1)
    assert table.discovery_policy_id == SALES
    assert table.maintenance_policy_id is None
    assert table.updated_at == T1


def test_attach_another_discovery_policy_replaces_the_attached_one():
    """A table holds one discovery policy, so attaching another replaces it."""
    table = managed()
    table.attach_discovery_policy(SALES, T1)
    table.attach_discovery_policy(EVERYTHING, T2)
    assert table.discovery_policy_id == EVERYTHING
    assert table.updated_at == T2


def test_attach_the_attached_discovery_policy_again_changes_nothing():
    """Attaching the policy already attached is a no-op, so the update time stays."""
    table = managed()
    table.attach_discovery_policy(SALES, T1)
    table.attach_discovery_policy(SALES, T2)
    assert table.updated_at == T1


def test_detach_the_attached_discovery_policy_clears_it():
    """Detaching the attached discovery policy leaves the table without one."""
    table = managed()
    table.attach_discovery_policy(SALES, T1)
    table.detach_discovery_policy(SALES, T2)
    assert table.discovery_policy_id is None
    assert table.updated_at == T2


def test_detach_a_discovery_policy_that_is_not_attached_is_refused():
    """Detaching another policy than the attached one raises PolicyNotAttached and changes nothing."""
    table = managed()
    table.attach_discovery_policy(SALES, T1)
    with pytest.raises(PolicyNotAttached, match=f"{EVERYTHING} is not attached to table iceberg.sales.orders"):
        table.detach_discovery_policy(EVERYTHING, T2)
    assert table.discovery_policy_id == SALES
    assert table.updated_at == T1


def test_attach_a_maintenance_policy_to_a_table_holding_none():
    """Attaching a maintenance policy where none is sets it."""
    table = managed()
    table.attach_maintenance_policy(NIGHTLY, T1)
    assert table.maintenance_policy_id == NIGHTLY
    assert table.updated_at == T1


def test_attach_another_maintenance_policy_replaces_the_attached_one():
    """A table holds one maintenance policy, so attaching another replaces it."""
    table = managed()
    table.attach_maintenance_policy(NIGHTLY, T1)
    table.attach_maintenance_policy(HOURLY, T2)
    assert table.maintenance_policy_id == HOURLY


def test_detach_the_attached_maintenance_policy_clears_it():
    """Detaching the attached maintenance policy leaves the table without one."""
    table = managed()
    table.attach_maintenance_policy(NIGHTLY, T1)
    table.detach_maintenance_policy(NIGHTLY, T2)
    assert table.maintenance_policy_id is None
    assert table.updated_at == T2


def test_detach_a_maintenance_policy_that_is_not_attached_is_refused():
    """Detaching another maintenance policy than the attached one raises PolicyNotAttached."""
    table = managed()
    table.attach_maintenance_policy(NIGHTLY, T1)
    with pytest.raises(PolicyNotAttached):
        table.detach_maintenance_policy(HOURLY, T2)
    assert table.maintenance_policy_id == NIGHTLY


@pytest.mark.parametrize("attach", ["discovery", "maintenance"])
def test_attach_to_a_dropped_table_is_refused(attach: str):
    """A dropped table never comes back, so no policy is attached to it."""
    table = dropped()
    with pytest.raises(InvalidTableTransition, match="table is dropped"):
        if attach == "discovery":
            table.attach_discovery_policy(SALES, T2)
        else:
            table.attach_maintenance_policy(NIGHTLY, T2)
    assert table.discovery_policy_id is None
    assert table.maintenance_policy_id is None


def test_mark_dropped_clears_both_policies():
    """A dropped table lets go of its policies, so they can still be deleted."""
    table = managed()
    table.attach_discovery_policy(SALES, T1)
    table.attach_maintenance_policy(NIGHTLY, T1)
    table.mark_dropped(T2)
    assert table.status is TableStatus.DROPPED
    assert table.discovery_policy_id is None
    assert table.maintenance_policy_id is None


def test_a_dropped_table_holds_no_policy():
    """A table built dropped with a policy of its own is refused, so a dropped row never pins a policy."""
    with pytest.raises(InvariantViolation, match="a dropped table holds no policy"):
        Table(
            id=TableId("u1"),
            name=NAME,
            status=TableStatus.DROPPED,
            decided_by=None,
            registered_at=T0,
            updated_at=T0,
            maintenance_policy_id=NIGHTLY,
        )


def test_detach_from_a_dropped_table_is_refused_as_not_attached():
    """A dropped table holds no policy, so a detach of one is refused as not attached."""
    with pytest.raises(PolicyNotAttached):
        dropped().detach_discovery_policy(SALES, T2)


def test_register_undecided_gives_an_undecided_table_decided_by_nothing():
    """A table attached to before discovery saw it is undecided: not managed, and decided by nothing yet."""
    table = Table.register_undecided(TableId("u1"), NAME, T0)
    assert table.status is TableStatus.UNDECIDED
    assert table.decided_by is None
    assert not table.is_managed
    assert table.registered_at == table.updated_at == T0
    assert table.version == 1
    assert table.discovery_policy_id is None
    assert table.maintenance_policy_id is None


def test_manage_an_undecided_table():
    """Discovery leaves the undecided status by managing the table."""
    table = Table.register_undecided(TableId("u1"), NAME, T0)
    table.manage(DECIDED_BY, T1)
    assert table.status is TableStatus.MANAGED
    assert table.decided_by == DECIDED_BY
    assert table.is_managed
    assert table.updated_at == T1


def test_unmanage_an_undecided_table():
    """Discovery leaves the undecided status by unmanaging the table, even when no policy decided it."""
    table = Table.register_undecided(TableId("u1"), NAME, T0)
    table.unmanage(None, T1)
    assert table.status is TableStatus.UNMANAGED
    assert table.decided_by is None
    assert table.updated_at == T1


def test_an_undecided_table_holds_its_policies_through_the_decision():
    """A policy attached to an undecided table stays attached once discovery decides it."""
    table = Table.register_undecided(TableId("u1"), NAME, T0)
    table.attach_discovery_policy(SALES, T0)
    table.manage(DECIDED_BY, T1)
    assert table.discovery_policy_id == SALES


def test_an_undecided_table_is_decided_by_nothing():
    """An undecided table names no decider, since no discovery has decided it yet."""
    with pytest.raises(InvariantViolation, match="an undecided table is decided by nothing"):
        Table(
            id=TableId("u1"),
            name=NAME,
            status=TableStatus.UNDECIDED,
            decided_by=DECIDED_BY,
            registered_at=T0,
            updated_at=T0,
        )
