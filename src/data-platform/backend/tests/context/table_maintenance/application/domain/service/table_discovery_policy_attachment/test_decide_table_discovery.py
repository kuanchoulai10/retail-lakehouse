"""Test decide_table_discovery: a table is decided by the policy of its nearest attachment."""

from __future__ import annotations

from datetime import UTC, datetime

from context.table_maintenance.application.domain.model.shared import PolicyTarget, PolicyTargetType
from context.table_maintenance.application.domain.model.table import TableName
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DEFAULT_DISCOVERY_POLICY_ID,
    DiscoveryDecision,
    DiscoveryMatch,
    DiscoveryOutcome,
    DiscoveryPolicyContent,
    TableDiscoveryPolicy,
    TableDiscoveryPolicyName,
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.domain.model.table_discovery_policy_attachment import (
    TableDiscoveryPolicyAttachment,
)
from context.table_maintenance.application.domain.service.table_discovery_policy_attachment import (
    decide_table_discovery,
)

NOW = datetime(2026, 11, 1, tzinfo=UTC)
ORDERS = TableName(catalog="iceberg", namespace="sales.eu", table="orders")
MANAGE_RULE = TableDiscoveryRuleId("dr-00000000000000000000000001")
MANAGE_ALL = TableDiscoveryPolicy.create(
    TableDiscoveryPolicyName(value="manage-all"),
    DiscoveryPolicyContent.from_primitives(
        {
            "no_match_outcome": "unmanage",
            "rules": [
                {
                    "id": MANAGE_RULE.value,
                    "outcome": "manage",
                    "conditions": [{"attribute": "table_name", "operator": "glob", "values": ["*"]}],
                }
            ],
        }
    ),
    NOW,
    new_rule_ids=[MANAGE_RULE],
)
UNMANAGE_ALL = TableDiscoveryPolicy.create(
    TableDiscoveryPolicyName(value="unmanage-all"),
    DiscoveryPolicyContent.from_primitives({"no_match_outcome": "unmanage", "rules": []}),
    NOW,
)
DEFAULT = TableDiscoveryPolicy.create_default(NOW)
POLICIES = {policy.id: policy for policy in (MANAGE_ALL, UNMANAGE_ALL, DEFAULT)}


def catalog_target(catalog: str) -> PolicyTarget:
    """Return a catalog target."""
    return PolicyTarget(type=PolicyTargetType.CATALOG, path=(catalog,))


def namespace_target(catalog: str, namespace: str) -> PolicyTarget:
    """Return a namespace target from a dot-joined namespace."""
    return PolicyTarget(type=PolicyTargetType.NAMESPACE, path=(catalog, *namespace.split(".")))


def table_target(name: TableName, table_uuid: str) -> PolicyTarget:
    """Return a table target at the given path, identified by its uuid."""
    return PolicyTarget(
        type=PolicyTargetType.TABLE,
        path=(name.catalog, *name.namespace.split("."), name.table),
        table_uuid=table_uuid,
    )


def attached(target: PolicyTarget, policy: TableDiscoveryPolicy) -> TableDiscoveryPolicyAttachment:
    """Return a new attachment of the policy to the target."""
    return TableDiscoveryPolicyAttachment.attach(target, policy.id, NOW)


def test_the_table_attachment_beats_a_managing_catalog():
    """The default attached to a table opts it out of the catalog's managing policy."""
    decision = decide_table_discovery(
        ORDERS,
        "u1",
        [attached(catalog_target("iceberg"), MANAGE_ALL), attached(table_target(ORDERS, "u1"), DEFAULT)],
        {MANAGE_ALL.id: MANAGE_ALL, DEFAULT.id: DEFAULT},
    )

    assert (decision.outcome, decision.match.policy_id) == (DiscoveryOutcome.UNMANAGE, DEFAULT_DISCOVERY_POLICY_ID)


def test_the_deepest_namespace_wins():
    """``sales.eu`` is nearer to ``sales.eu.orders`` than ``sales``, so its policy decides."""
    decision = decide_table_discovery(
        ORDERS,
        "u1",
        [
            attached(namespace_target("iceberg", "sales"), MANAGE_ALL),
            attached(namespace_target("iceberg", "sales.eu"), UNMANAGE_ALL),
        ],
        POLICIES,
    )

    assert (decision.outcome, decision.match.policy_id) == (DiscoveryOutcome.UNMANAGE, UNMANAGE_ALL.id)


def test_the_catalog_decides_when_nothing_nearer_is_attached():
    """With only the catalog attached, its policy decides, naming the rule that matched."""
    decision = decide_table_discovery(ORDERS, "u1", [attached(catalog_target("iceberg"), MANAGE_ALL)], POLICIES)

    assert decision == DiscoveryDecision(
        outcome=DiscoveryOutcome.MANAGE,
        match=DiscoveryMatch(policy_id=MANAGE_ALL.id, policy_version=1, rule_id=MANAGE_RULE),
    )


def test_nothing_attached_is_the_default_v1():
    """With no attachment on the walk, the platform default decides at version 1 with no rule."""
    decision = decide_table_discovery(ORDERS, "u1", [], {})

    assert decision == DiscoveryDecision(
        outcome=DiscoveryOutcome.UNMANAGE,
        match=DiscoveryMatch(policy_id=DEFAULT_DISCOVERY_POLICY_ID, policy_version=1, rule_id=None),
    )


def test_attachments_off_the_walk_are_ignored():
    """An attachment on another catalog or another namespace never decides the table."""
    decision = decide_table_discovery(
        ORDERS,
        "u1",
        [attached(catalog_target("other"), MANAGE_ALL), attached(namespace_target("iceberg", "hr"), MANAGE_ALL)],
        POLICIES,
    )

    assert decision.match.policy_id == DEFAULT_DISCOVERY_POLICY_ID


def test_a_table_is_found_by_uuid_not_by_path():
    """A table attachment made under an old name still decides the table with the same uuid."""
    old_name = TableName(catalog="iceberg", namespace="staging", table="orders_old")
    decision = decide_table_discovery(
        ORDERS,
        "u1",
        [attached(catalog_target("iceberg"), UNMANAGE_ALL), attached(table_target(old_name, "u1"), MANAGE_ALL)],
        POLICIES,
    )

    assert (decision.outcome, decision.match.policy_id) == (DiscoveryOutcome.MANAGE, MANAGE_ALL.id)


def test_another_tables_attachment_never_decides():
    """A table attachment with the same path but another uuid is another table's."""
    decision = decide_table_discovery(ORDERS, "u1", [attached(table_target(ORDERS, "u2"), MANAGE_ALL)], POLICIES)

    assert decision.match.policy_id == DEFAULT_DISCOVERY_POLICY_ID


def test_an_attachment_without_its_policy_is_skipped():
    """The namespace's policy is gone (a race with its delete), so the catalog's policy decides."""
    decision = decide_table_discovery(
        ORDERS,
        "u1",
        [
            attached(catalog_target("iceberg"), MANAGE_ALL),
            attached(namespace_target("iceberg", "sales.eu"), UNMANAGE_ALL),
        ],
        {MANAGE_ALL.id: MANAGE_ALL},
    )

    assert (decision.outcome, decision.match.policy_id) == (DiscoveryOutcome.MANAGE, MANAGE_ALL.id)
