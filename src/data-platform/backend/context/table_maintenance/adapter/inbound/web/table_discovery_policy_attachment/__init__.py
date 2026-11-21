"""Web adapter for the table_discovery_policy_attachment group: a discovery policy's attachments."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.table_discovery_policy_attachment.dto import (
    AttachTableDiscoveryPolicyApiRequest,
    ListedTableDiscoveryPolicyAttachmentApiResponse,
    TableDiscoveryPolicyAttachmentApiResponse,
    TableDiscoveryPolicyAttachmentsApiResponse,
)
from context.table_maintenance.adapter.inbound.web.table_discovery_policy_attachment.router import (
    router,
)

__all__ = [
    "AttachTableDiscoveryPolicyApiRequest",
    "ListedTableDiscoveryPolicyAttachmentApiResponse",
    "TableDiscoveryPolicyAttachmentApiResponse",
    "TableDiscoveryPolicyAttachmentsApiResponse",
    "router",
]
