"""Outbound ports for the table_maintenance_policy_attachment group."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy_attachment import (
    PolicyTarget,
    PolicyTargetType,
    TableMaintenancePolicyAttachment,
    TableMaintenancePolicyAttachmentId,
)
from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment.table_maintenance_policy_attachments_repo import (  # noqa: E501
    TableMaintenancePolicyAttachmentsRepo,
)

__all__ = [
    "PolicyTarget",
    "PolicyTargetType",
    "TableMaintenancePolicyAttachment",
    "TableMaintenancePolicyAttachmentId",
    "TableMaintenancePolicyAttachmentsRepo",
    "TableMaintenancePolicyName",
]
