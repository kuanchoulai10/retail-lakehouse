"""Define the maintenance policy attachment and applicable policy DTOs; the target DTOs are shared (``web.shared``)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from context.table_maintenance.adapter.inbound.web.shared import (
    PolicyTargetApiRequest,
    PolicyTargetApiResponse,
)
from context.table_maintenance.adapter.inbound.web.table_maintenance_policy import (
    ExpireSnapshotsSpecApiRequest,
    MaintenanceTriggersApiRequest,
    RemoveOrphanFilesSpecApiRequest,
    RewriteDataFilesSpecApiRequest,
    RewriteManifestsSpecApiRequest,
)


class AttachTableMaintenancePolicyApiRequest(BaseModel):
    """Carry the target to attach the policy to; it replaces whatever is attached there."""

    model_config = ConfigDict(extra="forbid")

    target: PolicyTargetApiRequest


class TableMaintenancePolicyAttachmentApiResponse(BaseModel):
    """Describe a maintenance policy attached to a target, under the attachment's ``pa-`` id."""

    id: str
    target: PolicyTargetApiResponse
    policy_id: str
    policy_name: str
    attached_at: datetime


class ListedTableMaintenancePolicyAttachmentApiResponse(BaseModel):
    """Describe a listed attachment; ``orphaned`` when its target no longer exists in the catalog."""

    id: str
    target: PolicyTargetApiResponse
    policy_id: str
    policy_name: str
    attached_at: datetime
    orphaned: bool


class TableMaintenancePolicyAttachmentsApiResponse(BaseModel):
    """List a maintenance policy's attachments."""

    attachments: list[ListedTableMaintenancePolicyAttachmentApiResponse]


class ApplicableTableMaintenancePolicyApiResponse(BaseModel):
    """Describe the policy that applies after inheritance and the target it is attached to, null for the default."""

    id: str
    name: str
    version: int
    description: str
    on: MaintenanceTriggersApiRequest
    dry_run: bool
    rewrite_data_files: RewriteDataFilesSpecApiRequest | None
    rewrite_manifests: RewriteManifestsSpecApiRequest | None
    expire_snapshots: ExpireSnapshotsSpecApiRequest | None
    remove_orphan_files: RemoveOrphanFilesSpecApiRequest | None
    target: PolicyTargetApiResponse | None
