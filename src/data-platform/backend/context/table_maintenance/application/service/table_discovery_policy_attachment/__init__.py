"""Services for the table_discovery_policy_attachment group."""

from __future__ import annotations

from context.table_maintenance.application.service.table_discovery_policy_attachment.apply_discovery_change import (
    apply_discovery_change,
)
from context.table_maintenance.application.service.table_discovery_policy_attachment.attach_table_discovery_policy import (  # noqa: E501
    AttachTableDiscoveryPolicyService,
)
from context.table_maintenance.application.service.table_discovery_policy_attachment.detach_table_discovery_policy import (  # noqa: E501
    DetachTableDiscoveryPolicyService,
)
from context.table_maintenance.application.service.table_discovery_policy_attachment.list_table_discovery_policy_attachments import (  # noqa: E501
    ListTableDiscoveryPolicyAttachmentsService,
)
from context.table_maintenance.application.service.table_discovery_policy_attachment.read_scanned_catalogs import (
    read_scanned_catalogs,
)
from context.table_maintenance.application.service.table_discovery_policy_attachment.sync_discovery_schedules import (  # noqa: E501
    SyncDiscoverySchedulesService,
)

__all__ = [
    "AttachTableDiscoveryPolicyService",
    "DetachTableDiscoveryPolicyService",
    "ListTableDiscoveryPolicyAttachmentsService",
    "SyncDiscoverySchedulesService",
    "apply_discovery_change",
    "read_scanned_catalogs",
]
