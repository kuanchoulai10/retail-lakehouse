"""Web adapter for the table_discovery_policy group."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.table_discovery_policy.dto import (
    CreateTableDiscoveryPolicyApiRequest,
    DiscoveryRuleApiRequest,
    DiscoveryRuleApiResponse,
    ListedTableDiscoveryPolicyApiResponse,
    TableDiscoveryPoliciesApiResponse,
    TableDiscoveryPolicyApiResponse,
    TableDiscoveryPolicyVersionApiResponse,
    UpdateTableDiscoveryPolicyApiRequest,
)
from context.table_maintenance.adapter.inbound.web.table_discovery_policy.router import (
    router,
)

__all__ = [
    "CreateTableDiscoveryPolicyApiRequest",
    "DiscoveryRuleApiRequest",
    "DiscoveryRuleApiResponse",
    "ListedTableDiscoveryPolicyApiResponse",
    "TableDiscoveryPoliciesApiResponse",
    "TableDiscoveryPolicyApiResponse",
    "TableDiscoveryPolicyVersionApiResponse",
    "UpdateTableDiscoveryPolicyApiRequest",
    "router",
]
