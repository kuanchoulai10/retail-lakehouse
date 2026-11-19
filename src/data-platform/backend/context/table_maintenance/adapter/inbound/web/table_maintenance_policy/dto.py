"""Define the maintenance policy API DTOs.

The content shapes (``...PolicyApiRequest`` and below) are what a client writes and what every
policy response echoes; their schema is the validation one in both directions, so the generated
client has one type per shape.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

_CONTENT_CONFIG = ConfigDict(extra="forbid", json_schema_mode_override="validation")

type MaintenancePriorityApi = Literal["P0", "P1", "P2"]


class AtLeastApiRequest(BaseModel):
    """Carry a count condition: due when at least this many are found."""

    model_config = _CONTENT_CONFIG

    at_least: int


class SmallManifestsConditionApiRequest(BaseModel):
    """Carry the small-manifests condition; a null size falls back to the table's manifest target size."""

    model_config = _CONTENT_CONFIG

    at_least: int
    smaller_than_bytes: int | None = None


class RewriteDataFilesConditionsApiRequest(BaseModel):
    """Carry the compaction conditions; a missing one is not checked, the others combine with OR."""

    model_config = _CONTENT_CONFIG

    reducible_files: AtLeastApiRequest | None = None


class RewriteManifestsConditionsApiRequest(BaseModel):
    """Carry the manifest rewrite conditions; a missing one is not checked."""

    model_config = _CONTENT_CONFIG

    small_manifests: SmallManifestsConditionApiRequest | None = None


class ExpireSnapshotsConditionsApiRequest(BaseModel):
    """Carry the snapshot expiry conditions; a missing one is not checked."""

    model_config = _CONTENT_CONFIG

    expirable_snapshots: AtLeastApiRequest | None = None


class RemoveOrphanFilesConditionsApiRequest(BaseModel):
    """Carry the orphan file removal conditions; there are none, so it is due once its cooldown passed."""

    model_config = _CONTENT_CONFIG


class RewriteDataFilesTriggerPolicyApiRequest(BaseModel):
    """Carry when compaction is due."""

    model_config = _CONTENT_CONFIG

    cooldown_seconds: int
    conditions: RewriteDataFilesConditionsApiRequest


class RewriteManifestsTriggerPolicyApiRequest(BaseModel):
    """Carry when a manifest rewrite is due."""

    model_config = _CONTENT_CONFIG

    cooldown_seconds: int
    conditions: RewriteManifestsConditionsApiRequest


class ExpireSnapshotsTriggerPolicyApiRequest(BaseModel):
    """Carry when snapshot expiry is due."""

    model_config = _CONTENT_CONFIG

    cooldown_seconds: int
    conditions: ExpireSnapshotsConditionsApiRequest


class RemoveOrphanFilesTriggerPolicyApiRequest(BaseModel):
    """Carry when orphan file removal is due."""

    model_config = _CONTENT_CONFIG

    cooldown_seconds: int
    conditions: RemoveOrphanFilesConditionsApiRequest


class PartialProgressApiRequest(BaseModel):
    """Carry whether compaction commits in parts, and at most how many."""

    model_config = _CONTENT_CONFIG

    enabled: bool
    max_commits: int | None = None


class RewriteDataFilesExecutionPolicyApiRequest(BaseModel):
    """Carry the values compaction is run with; a null target size falls back to the table property."""

    model_config = _CONTENT_CONFIG

    target_file_size_bytes: int | None = None
    min_input_files: int
    partial_progress: PartialProgressApiRequest


class RewriteManifestsExecutionPolicyApiRequest(BaseModel):
    """Carry the values a manifest rewrite is run with; there are none."""

    model_config = _CONTENT_CONFIG


class ExpireSnapshotsExecutionPolicyApiRequest(BaseModel):
    """Carry the values snapshot expiry is run with."""

    model_config = _CONTENT_CONFIG

    older_than_seconds: int
    retain_last: int


class RemoveOrphanFilesExecutionPolicyApiRequest(BaseModel):
    """Carry the values orphan file removal is run with."""

    model_config = _CONTENT_CONFIG

    older_than_seconds: int


class CompactionScopeApiRequest(BaseModel):
    """Carry whether compaction measures and rewrites per partition or across the table."""

    model_config = _CONTENT_CONFIG

    unit: Literal["partition", "table"]


class RewriteDataFilesPolicyApiRequest(BaseModel):
    """Carry the compaction policy: its switch, scope, trigger and execution."""

    model_config = _CONTENT_CONFIG

    enabled: bool
    scope: CompactionScopeApiRequest
    trigger_policy: RewriteDataFilesTriggerPolicyApiRequest
    execution_policy: RewriteDataFilesExecutionPolicyApiRequest


class RewriteManifestsPolicyApiRequest(BaseModel):
    """Carry the manifest rewrite policy."""

    model_config = _CONTENT_CONFIG

    enabled: bool
    trigger_policy: RewriteManifestsTriggerPolicyApiRequest
    execution_policy: RewriteManifestsExecutionPolicyApiRequest


class ExpireSnapshotsPolicyApiRequest(BaseModel):
    """Carry the snapshot expiry policy."""

    model_config = _CONTENT_CONFIG

    enabled: bool
    trigger_policy: ExpireSnapshotsTriggerPolicyApiRequest
    execution_policy: ExpireSnapshotsExecutionPolicyApiRequest


class RemoveOrphanFilesPolicyApiRequest(BaseModel):
    """Carry the orphan file removal policy."""

    model_config = _CONTENT_CONFIG

    enabled: bool
    trigger_policy: RemoveOrphanFilesTriggerPolicyApiRequest
    execution_policy: RemoveOrphanFilesExecutionPolicyApiRequest


class OperationPoliciesApiRequest(BaseModel):
    """Carry one policy per maintenance operation."""

    model_config = _CONTENT_CONFIG

    rewrite_data_files: RewriteDataFilesPolicyApiRequest
    rewrite_manifests: RewriteManifestsPolicyApiRequest
    expire_snapshots: ExpireSnapshotsPolicyApiRequest
    remove_orphan_files: RemoveOrphanFilesPolicyApiRequest


class CreateTableMaintenancePolicyApiRequest(BaseModel):
    """Carry a new policy's name and its whole content."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    reconcile_interval_seconds: int
    dry_run: bool
    priority: MaintenancePriorityApi = "P2"
    operations: OperationPoliciesApiRequest


class UpdateTableMaintenancePolicyApiRequest(BaseModel):
    """Carry a policy's whole new content and the version it was edited from."""

    model_config = ConfigDict(extra="forbid")

    version: int
    description: str
    reconcile_interval_seconds: int
    dry_run: bool
    priority: MaintenancePriorityApi = "P2"
    operations: OperationPoliciesApiRequest


class TableMaintenancePolicyApiResponse(BaseModel):
    """Describe a policy at its current version."""

    id: str
    name: str
    version: int
    description: str
    reconcile_interval_seconds: int
    dry_run: bool
    priority: MaintenancePriorityApi
    operations: OperationPoliciesApiRequest
    created_at: datetime
    updated_at: datetime


class ListedTableMaintenancePolicyApiResponse(BaseModel):
    """Describe a listed policy at its current version with how many targets it is attached to."""

    id: str
    name: str
    version: int
    description: str
    reconcile_interval_seconds: int
    dry_run: bool
    priority: MaintenancePriorityApi
    operations: OperationPoliciesApiRequest
    created_at: datetime
    updated_at: datetime
    attachment_count: int


class TableMaintenancePoliciesApiResponse(BaseModel):
    """List every policy."""

    policies: list[ListedTableMaintenancePolicyApiResponse]


class TableMaintenancePolicyVersionApiResponse(BaseModel):
    """Describe one stored version of a policy; ``created_at`` is when that version was written."""

    id: str
    name: str
    version: int
    description: str
    reconcile_interval_seconds: int
    dry_run: bool
    priority: MaintenancePriorityApi
    operations: OperationPoliciesApiRequest
    created_at: datetime
