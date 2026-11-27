"""Test ManagementDecision and DecidedBy: what decided a table, or that nothing did."""

from __future__ import annotations

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.shared import TableDiscoveryPolicyId
from context.table_maintenance.application.domain.model.table_discovery_policy import DecidedBy, ManagementDecision

_POLICY_ID = TableDiscoveryPolicyId("dp-00000000000000000000000001")


def test_a_decision_to_manage_names_what_decided() -> None:
    """A decision to manage names what decided."""
    decided_by = DecidedBy(policy_id=_POLICY_ID, policy_version=2, rule_position=3)

    decision = ManagementDecision(manage=True, decided_by=decided_by)

    assert decision.manage is True
    assert decision.decided_by == decided_by


def test_a_decision_to_manage_without_a_decider_is_refused() -> None:
    """A decision to manage without a decider is refused."""
    with pytest.raises(InvariantViolation):
        ManagementDecision(manage=True, decided_by=None)


def test_a_decision_not_to_manage_may_name_a_policy_no_rule_matched() -> None:
    """A decision not to manage may name a policy no rule matched."""
    decided_by = DecidedBy(policy_id=_POLICY_ID, policy_version=1, rule_position=None)

    assert ManagementDecision(manage=False, decided_by=decided_by).decided_by == decided_by


def test_nothing_attached_manages_nothing_and_names_no_decider() -> None:
    """Nothing attached manages nothing and names no decider."""
    assert ManagementDecision.nothing_attached() == ManagementDecision(manage=False, decided_by=None)


@pytest.mark.parametrize(("version", "position"), [(0, 1), (1, 0)])
def test_decided_by_counts_from_one(version: int, position: int) -> None:
    """Decided by counts from one."""
    with pytest.raises(InvariantViolation):
        DecidedBy(policy_id=_POLICY_ID, policy_version=version, rule_position=position)
