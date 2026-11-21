"""Web adapter for the table_maintenance_policy_attachment group: policy attachments."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.table_maintenance_policy_attachment.dto import (
    AttachTableMaintenancePolicyApiRequest,
    ListedTableMaintenancePolicyAttachmentApiResponse,
    TableMaintenancePolicyAttachmentApiResponse,
    TableMaintenancePolicyAttachmentsApiResponse,
)
from context.table_maintenance.adapter.inbound.web.table_maintenance_policy_attachment.router import (
    router,
)

__all__ = [
    "AttachTableMaintenancePolicyApiRequest",
    "ListedTableMaintenancePolicyAttachmentApiResponse",
    "TableMaintenancePolicyAttachmentApiResponse",
    "TableMaintenancePolicyAttachmentsApiResponse",
    "router",
]
