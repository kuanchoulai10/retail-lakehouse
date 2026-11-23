"""Test the table discovery policy attachment aggregate."""

from __future__ import annotations

from datetime import UTC, datetime

from context.table_maintenance.application.domain.model.shared import (
    PolicyTarget,
    PolicyTargetType,
    TableDiscoveryPolicyId,
)
from context.table_maintenance.application.domain.model.table_discovery_policy_attachment import (
    TableDiscoveryPolicyAttachment,
)
from shared_kernel import prefixed_id_pattern

NOW = datetime(2026, 11, 1, tzinfo=UTC)
LATER = datetime(2026, 11, 2, tzinfo=UTC)
CATALOG = PolicyTarget(type=PolicyTargetType.CATALOG, path=("iceberg",))


def test_attach_issues_a_new_da_id():
    """Attaching issues a random da- id, never one derived from the target."""
    policy_id = TableDiscoveryPolicyId.new()
    first = TableDiscoveryPolicyAttachment.attach(CATALOG, policy_id, NOW)
    second = TableDiscoveryPolicyAttachment.attach(CATALOG, policy_id, NOW)

    assert prefixed_id_pattern("da").fullmatch(first.id.value)
    assert first.id != second.id
    assert (first.target, first.policy_id, first.attached_at) == (CATALOG, policy_id, NOW)


def test_replace_policy_keeps_the_attachment_id():
    """Replacing the policy points the same attachment at another policy, attached now."""
    attachment = TableDiscoveryPolicyAttachment.attach(CATALOG, TableDiscoveryPolicyId.new(), NOW)
    attachment_id = attachment.id
    other = TableDiscoveryPolicyId.new()

    attachment.replace_policy(other, LATER)

    assert (attachment.id, attachment.policy_id, attachment.attached_at) == (attachment_id, other, LATER)


def test_the_catalog_is_the_first_path_element():
    """A namespace or table attachment names its catalog first in its path."""
    table = PolicyTarget(type=PolicyTargetType.TABLE, path=("iceberg", "sales", "orders"), table_uuid="u1")
    namespace = PolicyTarget(type=PolicyTargetType.NAMESPACE, path=("lake", "sales"))
    policy_id = TableDiscoveryPolicyId.new()

    assert TableDiscoveryPolicyAttachment.attach(table, policy_id, NOW).catalog == "iceberg"
    assert TableDiscoveryPolicyAttachment.attach(namespace, policy_id, NOW).catalog == "lake"
    assert TableDiscoveryPolicyAttachment.attach(CATALOG, policy_id, NOW).catalog == "iceberg"
