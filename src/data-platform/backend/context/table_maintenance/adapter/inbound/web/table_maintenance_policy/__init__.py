"""Web adapter for the table_maintenance_policy group."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.table_maintenance_policy.attachments_dto import (
    AttachTableMaintenancePolicyApiRequest,
    ListedTableMaintenancePolicyAttachmentApiResponse,
    TableMaintenancePolicyAttachmentApiResponse,
    TableMaintenancePolicyAttachmentsApiResponse,
)
from context.table_maintenance.adapter.inbound.web.table_maintenance_policy.attachments_router import (
    attachments_router,
)
from context.table_maintenance.adapter.inbound.web.table_maintenance_policy.dto import (
    AtMostApiRequest,
    CatalogCommitTriggerApiRequest,
    CreateTableMaintenancePolicyApiRequest,
    ExpireSnapshotsOptionsApiRequest,
    ExpireSnapshotsSpecApiRequest,
    ExpireSnapshotsTargetApiRequest,
    ListedTableMaintenancePolicyApiResponse,
    MaintenanceTriggersApiRequest,
    RemoveOrphanFilesOptionsApiRequest,
    RemoveOrphanFilesSpecApiRequest,
    RemoveOrphanFilesTargetApiRequest,
    RewriteDataFilesOptionsApiRequest,
    RewriteDataFilesSpecApiRequest,
    RewriteDataFilesTargetApiRequest,
    RewriteManifestsOptionsApiRequest,
    RewriteManifestsSpecApiRequest,
    RewriteManifestsTargetApiRequest,
    ScheduleTriggerApiRequest,
    TableMaintenancePoliciesApiResponse,
    TableMaintenancePolicyApiResponse,
    TableMaintenancePolicyVersionApiResponse,
    UpdateTableMaintenancePolicyApiRequest,
)
from context.table_maintenance.adapter.inbound.web.table_maintenance_policy.router import (
    router,
)

__all__ = [
    "AtMostApiRequest",
    "AttachTableMaintenancePolicyApiRequest",
    "CatalogCommitTriggerApiRequest",
    "CreateTableMaintenancePolicyApiRequest",
    "ExpireSnapshotsOptionsApiRequest",
    "ExpireSnapshotsSpecApiRequest",
    "ExpireSnapshotsTargetApiRequest",
    "ListedTableMaintenancePolicyApiResponse",
    "ListedTableMaintenancePolicyAttachmentApiResponse",
    "MaintenanceTriggersApiRequest",
    "RemoveOrphanFilesOptionsApiRequest",
    "RemoveOrphanFilesSpecApiRequest",
    "RemoveOrphanFilesTargetApiRequest",
    "RewriteDataFilesOptionsApiRequest",
    "RewriteDataFilesSpecApiRequest",
    "RewriteDataFilesTargetApiRequest",
    "RewriteManifestsOptionsApiRequest",
    "RewriteManifestsSpecApiRequest",
    "RewriteManifestsTargetApiRequest",
    "ScheduleTriggerApiRequest",
    "TableMaintenancePoliciesApiResponse",
    "TableMaintenancePolicyApiResponse",
    "TableMaintenancePolicyAttachmentApiResponse",
    "TableMaintenancePolicyAttachmentsApiResponse",
    "TableMaintenancePolicyVersionApiResponse",
    "UpdateTableMaintenancePolicyApiRequest",
    "attachments_router",
    "router",
]
