"""Sample discovery policies, targets and attachments shared by the discovery attachment tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    PolicyTarget,
    PolicyTargetType,
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DiscoveryPolicyContent,
    TableDiscoveryPolicy,
    TableDiscoveryPolicyName,
)
from context.table_maintenance.application.domain.model.table_discovery_policy_attachment import (
    TableDiscoveryPolicyAttachment,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table import TableName

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
UNMANAGE_ALL = TableDiscoveryPolicy.create(
    TableDiscoveryPolicyName(value="unmanage-all"),
    DiscoveryPolicyContent.from_primitives({"no_match_outcome": "unmanage", "rules": []}),
    NOW,
)
MANAGE_BY_DEFAULT = TableDiscoveryPolicy.create(
    TableDiscoveryPolicyName(value="manage-by-default"),
    DiscoveryPolicyContent.from_primitives({"no_match_outcome": "manage", "rules": []}),
    NOW,
)
DEFAULT = TableDiscoveryPolicy.create_default(NOW)
POLICIES = {policy.id: policy for policy in (MANAGE_ALL, UNMANAGE_ALL, MANAGE_BY_DEFAULT, DEFAULT)}


def catalog_target(catalog: str) -> PolicyTarget:
    """Return a catalog target."""
    return PolicyTarget(type=PolicyTargetType.CATALOG, path=(catalog,))


def namespace_target(catalog: str, namespace: str) -> PolicyTarget:
    """Return a namespace target from a dot-joined namespace."""
    return PolicyTarget(type=PolicyTargetType.NAMESPACE, path=(catalog, *namespace.split(".")))


def table_target(name: TableName, table_uuid: str) -> PolicyTarget:
    """Return a table target at the table's path, identified by its uuid."""
    return PolicyTarget(
        type=PolicyTargetType.TABLE,
        path=(name.catalog, *name.namespace.split("."), name.table),
        table_uuid=table_uuid,
    )


def attached(target: PolicyTarget, policy: TableDiscoveryPolicy) -> TableDiscoveryPolicyAttachment:
    """Return a new attachment of the policy to the target."""
    return TableDiscoveryPolicyAttachment.attach(target, policy.id, NOW)
