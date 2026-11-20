"""Define the maintenance policy API DTOs.

The content shapes (``...ApiRequest`` below the create and update bodies) are what a client writes
and what every policy response echoes; their schema is the validation one in both directions, so the
generated client has one type per shape. An options object writes only the options that are set.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

_CONTENT_CONFIG = ConfigDict(extra="forbid", json_schema_mode_override="validation")
_IS_DEFAULT = "Whether this is the platform default policy, which applies where nothing is attached."


def _is_unset(value: object) -> bool:
    return value is None


_LEFT_OUT_WHEN_UNSET = Field(exclude_if=_is_unset)
"""An option that is not set is not written, as the stored content does."""


class ScheduleTriggerApiRequest(BaseModel):
    """Check the table at least this often, from 60 seconds to 7 days."""

    model_config = _CONTENT_CONFIG

    every_seconds: int


class CatalogCommitTriggerApiRequest(BaseModel):
    """Check the table once the debounce window opened by the first catalog commit closes (0 to 86400 seconds)."""

    model_config = _CONTENT_CONFIG

    debounce_seconds: int = 300


class MaintenanceTriggersApiRequest(BaseModel):
    """Carry when a table is checked; without ``catalog_commit`` commits do not trigger a check."""

    model_config = _CONTENT_CONFIG

    schedule: ScheduleTriggerApiRequest
    catalog_commit: CatalogCommitTriggerApiRequest | None = None


class AtMostApiRequest(BaseModel):
    """Carry a count target: the table is on target while the count stays at or under ``at_most``."""

    model_config = _CONTENT_CONFIG

    at_most: int


class RewriteDataFilesTargetApiRequest(BaseModel):
    """Carry the compaction target: reducible files at most this many, per partition or across the table."""

    model_config = _CONTENT_CONFIG

    reducible_files: AtMostApiRequest
    per: Literal["partition", "table"] = "partition"


class RewriteDataFilesOptionsApiRequest(BaseModel):
    """Carry the ``rewrite_data_files`` options; one left out is left to the procedure."""

    model_config = _CONTENT_CONFIG

    strategy: Annotated[Literal["binpack", "sort"] | None, _LEFT_OUT_WHEN_UNSET] = None
    sort_order: Annotated[str | None, _LEFT_OUT_WHEN_UNSET] = None
    min_input_files: Annotated[int | None, _LEFT_OUT_WHEN_UNSET] = None
    partial_progress_enabled: Annotated[bool | None, _LEFT_OUT_WHEN_UNSET] = None
    partial_progress_max_commits: Annotated[int | None, _LEFT_OUT_WHEN_UNSET] = None
    max_concurrent_file_group_rewrites: Annotated[int | None, _LEFT_OUT_WHEN_UNSET] = None
    rewrite_all: Annotated[bool | None, _LEFT_OUT_WHEN_UNSET] = None
    delete_file_threshold: Annotated[int | None, _LEFT_OUT_WHEN_UNSET] = None
    remove_dangling_deletes: Annotated[bool | None, _LEFT_OUT_WHEN_UNSET] = None
    max_file_group_size_bytes: Annotated[int | None, _LEFT_OUT_WHEN_UNSET] = None


class RewriteManifestsTargetApiRequest(BaseModel):
    """Carry the manifest target: manifests under the table's manifest target size at most this many."""

    model_config = _CONTENT_CONFIG

    small_manifests: AtMostApiRequest


class RewriteManifestsOptionsApiRequest(BaseModel):
    """Carry the ``rewrite_manifests`` options; one left out is left to the procedure."""

    model_config = _CONTENT_CONFIG

    use_caching: Annotated[bool | None, _LEFT_OUT_WHEN_UNSET] = None


class ExpireSnapshotsTargetApiRequest(BaseModel):
    """Carry the retention target; a value left out falls back to the table property, then Iceberg's default.

    The count is at most 2147483647 and the age at most 3153600000 seconds (100 years).
    """

    model_config = _CONTENT_CONFIG

    min_snapshots_to_keep: int | None = None
    max_snapshot_age_seconds: int | None = None


class ExpireSnapshotsOptionsApiRequest(BaseModel):
    """Carry the ``expire_snapshots`` options; one left out is left to the procedure."""

    model_config = _CONTENT_CONFIG

    max_concurrent_deletes: Annotated[int | None, _LEFT_OUT_WHEN_UNSET] = None
    stream_results: Annotated[bool | None, _LEFT_OUT_WHEN_UNSET] = None


class RemoveOrphanFilesTargetApiRequest(BaseModel):
    """Carry the orphan file target: files older than this many seconds, from 86400 to 3153600000 (100 years)."""

    model_config = _CONTENT_CONFIG

    older_than_seconds: int


class RemoveOrphanFilesOptionsApiRequest(BaseModel):
    """Carry the ``remove_orphan_files`` options; one left out is left to the procedure."""

    model_config = _CONTENT_CONFIG

    max_concurrent_deletes: Annotated[int | None, _LEFT_OUT_WHEN_UNSET] = None
    prefix_mismatch_mode: Annotated[Literal["ERROR", "IGNORE", "DELETE"] | None, _LEFT_OUT_WHEN_UNSET] = None


class RewriteDataFilesSpecApiRequest(BaseModel):
    """Carry the compaction block: its target and its options."""

    model_config = _CONTENT_CONFIG

    target: RewriteDataFilesTargetApiRequest
    options: RewriteDataFilesOptionsApiRequest | None = None


class RewriteManifestsSpecApiRequest(BaseModel):
    """Carry the manifest rewrite block: its target and its options."""

    model_config = _CONTENT_CONFIG

    target: RewriteManifestsTargetApiRequest
    options: RewriteManifestsOptionsApiRequest | None = None


class ExpireSnapshotsSpecApiRequest(BaseModel):
    """Carry the snapshot expiry block: its target and its options."""

    model_config = _CONTENT_CONFIG

    target: ExpireSnapshotsTargetApiRequest
    options: ExpireSnapshotsOptionsApiRequest | None = None


class RemoveOrphanFilesSpecApiRequest(BaseModel):
    """Carry the orphan file removal block: its target and its options."""

    model_config = _CONTENT_CONFIG

    target: RemoveOrphanFilesTargetApiRequest
    options: RemoveOrphanFilesOptionsApiRequest | None = None


class CreateTableMaintenancePolicyApiRequest(BaseModel):
    """Carry a new policy's name and its whole content; an operation block left out is not done."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    on: MaintenanceTriggersApiRequest
    dry_run: bool = False
    rewrite_data_files: RewriteDataFilesSpecApiRequest | None = None
    rewrite_manifests: RewriteManifestsSpecApiRequest | None = None
    expire_snapshots: ExpireSnapshotsSpecApiRequest | None = None
    remove_orphan_files: RemoveOrphanFilesSpecApiRequest | None = None


class UpdateTableMaintenancePolicyApiRequest(BaseModel):
    """Carry a policy's whole new content and the version it was edited from; a block left out is removed."""

    model_config = ConfigDict(extra="forbid")

    version: int
    description: str
    on: MaintenanceTriggersApiRequest
    dry_run: bool = False
    rewrite_data_files: RewriteDataFilesSpecApiRequest | None = None
    rewrite_manifests: RewriteManifestsSpecApiRequest | None = None
    expire_snapshots: ExpireSnapshotsSpecApiRequest | None = None
    remove_orphan_files: RemoveOrphanFilesSpecApiRequest | None = None


class TableMaintenancePolicyApiResponse(BaseModel):
    """Describe a policy at its current version."""

    id: str
    name: str
    is_default: bool = Field(description=_IS_DEFAULT)
    version: int
    description: str
    on: MaintenanceTriggersApiRequest
    dry_run: bool
    rewrite_data_files: RewriteDataFilesSpecApiRequest | None
    rewrite_manifests: RewriteManifestsSpecApiRequest | None
    expire_snapshots: ExpireSnapshotsSpecApiRequest | None
    remove_orphan_files: RemoveOrphanFilesSpecApiRequest | None
    created_at: datetime
    updated_at: datetime


class ListedTableMaintenancePolicyApiResponse(BaseModel):
    """Describe a listed policy at its current version with how many targets it is attached to."""

    id: str
    name: str
    is_default: bool = Field(description=_IS_DEFAULT)
    version: int
    description: str
    on: MaintenanceTriggersApiRequest
    dry_run: bool
    rewrite_data_files: RewriteDataFilesSpecApiRequest | None
    rewrite_manifests: RewriteManifestsSpecApiRequest | None
    expire_snapshots: ExpireSnapshotsSpecApiRequest | None
    remove_orphan_files: RemoveOrphanFilesSpecApiRequest | None
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
    is_default: bool = Field(description=_IS_DEFAULT)
    version: int
    description: str
    on: MaintenanceTriggersApiRequest
    dry_run: bool
    rewrite_data_files: RewriteDataFilesSpecApiRequest | None
    rewrite_manifests: RewriteManifestsSpecApiRequest | None
    expire_snapshots: ExpireSnapshotsSpecApiRequest | None
    remove_orphan_files: RemoveOrphanFilesSpecApiRequest | None
    created_at: datetime
