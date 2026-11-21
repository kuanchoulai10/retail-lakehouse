"""Test scanned_catalogs: a catalog is scanned when one of its attachments points at a policy that can manage."""

from __future__ import annotations

from datetime import UTC, datetime

from context.table_maintenance.application.domain.model.shared import PolicyTarget, PolicyTargetType
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DiscoveryPolicyContent,
    TableDiscoveryPolicy,
    TableDiscoveryPolicyName,
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.domain.model.table_discovery_policy_attachment import (
    TableDiscoveryPolicyAttachment,
)
from context.table_maintenance.application.domain.service.table_discovery_policy_attachment import (
    scanned_catalogs,
)

NOW = datetime(2026, 11, 1, tzinfo=UTC)
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
MANAGE_BY_DEFAULT = TableDiscoveryPolicy.create(
    TableDiscoveryPolicyName(value="manage-by-default"),
    DiscoveryPolicyContent.from_primitives({"no_match_outcome": "manage", "rules": []}),
    NOW,
)
DEFAULT = TableDiscoveryPolicy.create_default(NOW)
POLICIES = {policy.id: policy for policy in (MANAGE_ALL, MANAGE_BY_DEFAULT, DEFAULT)}


def catalog_target(catalog: str) -> PolicyTarget:
    """Return a catalog target."""
    return PolicyTarget(type=PolicyTargetType.CATALOG, path=(catalog,))


def namespace_target(catalog: str, namespace: str) -> PolicyTarget:
    """Return a namespace target from a dot-joined namespace."""
    return PolicyTarget(type=PolicyTargetType.NAMESPACE, path=(catalog, *namespace.split(".")))


def table_target(catalog: str, namespace: str, table: str, table_uuid: str) -> PolicyTarget:
    """Return a table target at the given path, identified by its uuid."""
    return PolicyTarget(
        type=PolicyTargetType.TABLE, path=(catalog, *namespace.split("."), table), table_uuid=table_uuid
    )


def attached(target: PolicyTarget, policy: TableDiscoveryPolicy) -> TableDiscoveryPolicyAttachment:
    """Return a new attachment of the policy to the target."""
    return TableDiscoveryPolicyAttachment.attach(target, policy.id, NOW)


def test_a_catalog_is_scanned_when_a_policy_in_it_can_manage():
    """A namespace attachment of a managing rule scans its catalog; a catalog holding only the default is not."""
    assert scanned_catalogs(
        [attached(namespace_target("iceberg", "sales"), MANAGE_ALL), attached(catalog_target("other"), DEFAULT)],
        {MANAGE_ALL.id: MANAGE_ALL, DEFAULT.id: DEFAULT},
    ) == ("iceberg",)


def test_a_no_match_outcome_of_manage_scans_the_catalog():
    """A policy with no rule that manages everything it does not match can manage."""
    assert scanned_catalogs([attached(catalog_target("iceberg"), MANAGE_BY_DEFAULT)], POLICIES) == ("iceberg",)


def test_a_table_attachment_scans_its_catalog():
    """A table attachment's catalog is the first element of its path."""
    attachment = attached(table_target("iceberg", "sales", "orders", "u1"), MANAGE_ALL)

    assert scanned_catalogs([attachment], POLICIES) == ("iceberg",)


def test_scanned_catalogs_are_sorted_and_unique():
    """Each catalog is listed once, by name, however many managing attachments it holds."""
    attachments = [
        attached(catalog_target("zeta"), MANAGE_ALL),
        attached(namespace_target("alpha", "sales"), MANAGE_ALL),
        attached(catalog_target("alpha"), MANAGE_BY_DEFAULT),
        attached(catalog_target("mid"), DEFAULT),
    ]

    assert scanned_catalogs(attachments, POLICIES) == ("alpha", "zeta")


def test_an_attachment_without_its_policy_scans_nothing():
    """An attachment whose policy is gone (a race with its delete) is skipped."""
    assert scanned_catalogs([attached(catalog_target("iceberg"), MANAGE_ALL)], {}) == ()


def test_nothing_attached_scans_nothing():
    """With no attachment no catalog is scanned."""
    assert scanned_catalogs([], POLICIES) == ()
