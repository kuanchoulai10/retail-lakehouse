"""Web adapter for the table_maintenance_policy group."""

from __future__ import annotations

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
    "CatalogCommitTriggerApiRequest",
    "CreateTableMaintenancePolicyApiRequest",
    "ExpireSnapshotsOptionsApiRequest",
    "ExpireSnapshotsSpecApiRequest",
    "ExpireSnapshotsTargetApiRequest",
    "ListedTableMaintenancePolicyApiResponse",
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
    "TableMaintenancePolicyVersionApiResponse",
    "UpdateTableMaintenancePolicyApiRequest",
    "router",
]
