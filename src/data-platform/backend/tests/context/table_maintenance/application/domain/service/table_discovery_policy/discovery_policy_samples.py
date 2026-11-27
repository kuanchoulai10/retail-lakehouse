"""Sample discovery policies and targets shared by the discovery tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    PolicyTarget,
    PolicyTargetType,
)
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DiscoveryRule,
    DiscoveryRules,
    RuleAction,
    TableDiscoveryPolicy,
    TableDiscoveryPolicyName,
    TableNamePattern,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table import TableName

NOW = datetime(2026, 11, 1, tzinfo=UTC)


def rules(*specs: tuple[str, str]) -> DiscoveryRules:
    """Return discovery rules from ``(action, table name pattern)`` pairs, in order."""
    return DiscoveryRules(
        rules=tuple(
            DiscoveryRule(action=RuleAction(action), table_name_pattern=TableNamePattern(value=pattern))
            for action, pattern in specs
        )
    )


MANAGE_ALL = TableDiscoveryPolicy.create(TableDiscoveryPolicyName(value="manage-all"), "", rules(("include", "*")), NOW)
UNMANAGE_ALL = TableDiscoveryPolicy.create(
    TableDiscoveryPolicyName(value="unmanage-all"), "", rules(("exclude", "*")), NOW
)
MANAGE_ORDERS = TableDiscoveryPolicy.create(
    TableDiscoveryPolicyName(value="manage-orders"), "", rules(("include", "orders")), NOW
)
POLICIES = {policy.id: policy for policy in (MANAGE_ALL, UNMANAGE_ALL, MANAGE_ORDERS)}


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
