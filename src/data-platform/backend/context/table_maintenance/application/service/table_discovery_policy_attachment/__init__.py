"""Services for the table_discovery_policy_attachment group."""

from __future__ import annotations

from context.table_maintenance.application.service.table_discovery_policy_attachment.attach_table_discovery_policy import (  # noqa: E501
    AttachTableDiscoveryPolicyService,
)
from context.table_maintenance.application.service.table_discovery_policy_attachment.detach_table_discovery_policy import (  # noqa: E501
    DetachTableDiscoveryPolicyService,
)
from context.table_maintenance.application.service.table_discovery_policy_attachment.list_table_discovery_policy_attachments import (  # noqa: E501
    ListTableDiscoveryPolicyAttachmentsService,
)

__all__ = [
    "AttachTableDiscoveryPolicyService",
    "DetachTableDiscoveryPolicyService",
    "ListTableDiscoveryPolicyAttachmentsService",
]
