"""Outbound ports for the table_discovery_policy_attachment group."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import PolicyTarget, PolicyTargetType
from context.table_maintenance.application.domain.model.table_discovery_policy import TableDiscoveryPolicyId
from context.table_maintenance.application.domain.model.table_discovery_policy_attachment import (
    TableDiscoveryPolicyAttachment,
    TableDiscoveryPolicyAttachmentId,
)
from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment.sync_discovery_schedules.gateway import (  # noqa: E501
    SyncDiscoverySchedulesGateway,
)
from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment.sync_discovery_schedules.input import (  # noqa: E501
    SyncDiscoverySchedulesGatewayInput,
)
from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment.table_discovery_policy_attachments_repo import (  # noqa: E501
    TableDiscoveryPolicyAttachmentsRepo,
)

__all__ = [
    "PolicyTarget",
    "PolicyTargetType",
    "SyncDiscoverySchedulesGateway",
    "SyncDiscoverySchedulesGatewayInput",
    "TableDiscoveryPolicyAttachment",
    "TableDiscoveryPolicyAttachmentId",
    "TableDiscoveryPolicyAttachmentsRepo",
    "TableDiscoveryPolicyId",
]
