"""Test decide_table_discovery: the nearest discovery policy decides a table by its rules."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import TableDiscoveryPolicyId
from context.table_maintenance.application.domain.model.table import TableName
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DecidedBy,
    ManagementDecision,
)
from context.table_maintenance.application.domain.service.shared import NearestPolicy
from context.table_maintenance.application.domain.service.table_discovery_policy import decide_table_discovery
from tests.context.table_maintenance.application.domain.service.table_discovery_policy.discovery_policy_samples import (  # noqa: E501
    MANAGE_ALL,
    MANAGE_ORDERS,
    POLICIES,
    UNMANAGE_ALL,
    catalog_target,
    namespace_target,
)

ORDERS = TableName(catalog="iceberg", namespace="sales.eu", table="orders")
REFUNDS = TableName(catalog="iceberg", namespace="sales.eu", table="refunds")


def _nearest(policy_id: TableDiscoveryPolicyId) -> NearestPolicy[TableDiscoveryPolicyId]:
    return NearestPolicy(target=namespace_target("iceberg", "sales.eu"), policy_id=policy_id)


def test_no_nearest_policy_attaches_nothing():
    """With no policy on the walk nothing decides, which manages nothing."""
    assert decide_table_discovery(ORDERS, None, POLICIES) == ManagementDecision.nothing_attached()


def test_a_nearest_policy_that_is_gone_attaches_nothing():
    """A nearest policy missing from the policies read (deleted meanwhile) decides nothing."""
    assert decide_table_discovery(ORDERS, _nearest(TableDiscoveryPolicyId.new()), POLICIES) == (
        ManagementDecision.nothing_attached()
    )


def test_the_nearest_policy_decides_by_its_rules():
    """The nearest policy's last matching rule decides, naming the policy, its version and the rule."""
    decision = decide_table_discovery(ORDERS, _nearest(MANAGE_ORDERS.id), POLICIES)

    assert decision == ManagementDecision(
        manage=True, decided_by=DecidedBy(policy_id=MANAGE_ORDERS.id, policy_version=1, rule_position=1)
    )


def test_a_table_no_rule_matches_is_unmanaged_by_the_policy():
    """A table none of the nearest policy's rules match is not managed; the policy decided it, no rule did."""
    decision = decide_table_discovery(REFUNDS, _nearest(MANAGE_ORDERS.id), POLICIES)

    assert decision == ManagementDecision(
        manage=False, decided_by=DecidedBy(policy_id=MANAGE_ORDERS.id, policy_version=1, rule_position=None)
    )


def test_an_excluding_policy_unmanages():
    """An exclude rule that matches unmanages, whatever is placed above the nearest policy."""
    decision = decide_table_discovery(
        ORDERS, NearestPolicy(target=catalog_target("iceberg"), policy_id=UNMANAGE_ALL.id), POLICIES
    )

    assert decision.manage is False
    assert decision.decided_by is not None
    assert decision.decided_by.policy_id == UNMANAGE_ALL.id
    assert MANAGE_ALL.id in POLICIES
