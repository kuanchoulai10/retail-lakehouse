"""Web adapter for the table_discovery_policy group."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.table_discovery_policy.attachments_dto import (
    AttachTableDiscoveryPolicyApiRequest,
    ListedTableDiscoveryPolicyAttachmentApiResponse,
    TableDiscoveryPolicyAttachmentApiResponse,
    TableDiscoveryPolicyAttachmentsApiResponse,
)
from context.table_maintenance.adapter.inbound.web.table_discovery_policy.attachments_router import (
    attachments_router,
)
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
    "AttachTableDiscoveryPolicyApiRequest",
    "CreateTableDiscoveryPolicyApiRequest",
    "DiscoveryRuleApiRequest",
    "DiscoveryRuleApiResponse",
    "ListedTableDiscoveryPolicyApiResponse",
    "ListedTableDiscoveryPolicyAttachmentApiResponse",
    "TableDiscoveryPoliciesApiResponse",
    "TableDiscoveryPolicyApiResponse",
    "TableDiscoveryPolicyAttachmentApiResponse",
    "TableDiscoveryPolicyAttachmentsApiResponse",
    "TableDiscoveryPolicyVersionApiResponse",
    "UpdateTableDiscoveryPolicyApiRequest",
    "attachments_router",
    "router",
]
