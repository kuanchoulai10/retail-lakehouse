"""Outbound ports for the table_discovery_policy group."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import TableDiscoveryPolicyId
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DiscoveryRule,
    DiscoveryRules,
    RuleAction,
    StaleDiscoveryPolicyVersion,
    TableDiscoveryPolicy,
    TableDiscoveryPolicyName,
    TableDiscoveryPolicyVersion,
    TableNamePattern,
)
from context.table_maintenance.application.port.outbound.table_discovery_policy.table_discovery_policies_repo import (  # noqa: E501
    TableDiscoveryPoliciesRepo,
)

__all__ = [
    "DiscoveryRule",
    "DiscoveryRules",
    "RuleAction",
    "StaleDiscoveryPolicyVersion",
    "TableDiscoveryPoliciesRepo",
    "TableDiscoveryPolicy",
    "TableDiscoveryPolicyId",
    "TableDiscoveryPolicyName",
    "TableDiscoveryPolicyVersion",
    "TableNamePattern",
]
