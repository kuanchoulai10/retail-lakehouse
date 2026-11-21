"""Define the policy mapping and applicable policy API DTOs; the target DTOs are shared (``web.shared``)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from context.table_maintenance.adapter.inbound.web.shared import (
    DetachPolicyTargetApiRequest,
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


class DetachTableMaintenancePolicyApiRequest(BaseModel):
    """Carry the target to detach the policy from."""

    model_config = ConfigDict(extra="forbid")

    target: DetachPolicyTargetApiRequest


class TableMaintenancePolicyMappingApiResponse(BaseModel):
    """Describe a policy attached to a target."""

    target: PolicyTargetApiResponse
    policy_id: str
    policy_name: str
    attached_at: datetime


class ListedTableMaintenancePolicyMappingApiResponse(BaseModel):
    """Describe a listed mapping; ``orphaned`` when its target is no longer in the catalog."""

    target: PolicyTargetApiResponse
    policy_id: str
    policy_name: str
    attached_at: datetime
    orphaned: bool


class TableMaintenancePolicyMappingsApiResponse(BaseModel):
    """List a policy's mappings."""

    mappings: list[ListedTableMaintenancePolicyMappingApiResponse]


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
