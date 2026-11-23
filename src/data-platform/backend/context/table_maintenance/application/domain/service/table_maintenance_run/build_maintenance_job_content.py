"""Define the build_maintenance_job_content function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    ExpireSnapshotsOptions,
    RemoveOrphanFilesOptions,
    RewriteDataFilesOptions,
    RewriteManifestsOptions,
)
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    ExpireSnapshotsJobContent,
    RemoveOrphanFilesJobContent,
    RewriteDataFilesJobContent,
    RewriteManifestsJobContent,
)
from context.table_maintenance.application.domain.service.shared import (
    DEFAULT_ORPHAN_OLDER_THAN,
    resolve_snapshot_retention,
    resolve_target_file_size,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime

    from context.table_maintenance.application.domain.model.shared import SpecPartitions
    from context.table_maintenance.application.domain.model.table_maintenance_policy import (
        MaintenancePolicyContent,
    )
    from context.table_maintenance.application.domain.model.table_maintenance_run import MaintenanceJobContent


def build_maintenance_job_content(
    operation: MaintenanceOperation,
    policy: MaintenancePolicyContent,
    properties: Mapping[str, str],
    now: datetime,
    partitions: Sequence[SpecPartitions] = (),
) -> MaintenanceJobContent:
    """Return what one job of ``operation`` does on a table with ``properties``, under ``policy``.

    The options are the policy's. A compaction writes files of the table's target file size and is
    scoped to ``partitions`` (none means the whole table); an expiry keeps the retention of the
    policy's target, else the table's properties, else Iceberg's defaults; an orphan removal takes the
    target's age. An operation the policy leaves out (a manual run of it) runs with what the platform
    decides: no options, the table's retention and orphan files older than 3 days. Ages count back
    from ``now``, which must be timezone-aware.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if partitions and operation is not MaintenanceOperation.REWRITE_DATA_FILES:
        raise ValueError(f"only rewrite_data_files is scoped to partitions, not {operation}")
    match operation:
        case MaintenanceOperation.REWRITE_DATA_FILES:
            rewrite = policy.rewrite_data_files
            return RewriteDataFilesJobContent(
                target_file_size_bytes=resolve_target_file_size(properties),
                options=(rewrite.options if rewrite is not None else None) or RewriteDataFilesOptions(),
                partitions=tuple(partitions),
            )
        case MaintenanceOperation.REWRITE_MANIFESTS:
            manifests = policy.rewrite_manifests
            return RewriteManifestsJobContent(
                options=(manifests.options if manifests is not None else None) or RewriteManifestsOptions()
            )
        case MaintenanceOperation.EXPIRE_SNAPSHOTS:
            snapshots = policy.expire_snapshots
            retention = resolve_snapshot_retention(None if snapshots is None else snapshots.target, properties)
            return ExpireSnapshotsJobContent(
                older_than=now - retention.max_snapshot_age,
                retain_last=retention.min_snapshots_to_keep,
                options=(snapshots.options if snapshots is not None else None) or ExpireSnapshotsOptions(),
            )
        case MaintenanceOperation.REMOVE_ORPHAN_FILES:
            orphans = policy.remove_orphan_files
            if orphans is None:
                return RemoveOrphanFilesJobContent(older_than=now - DEFAULT_ORPHAN_OLDER_THAN)
            return RemoveOrphanFilesJobContent(
                older_than=now - orphans.target.older_than,
                options=orphans.options or RemoveOrphanFilesOptions(),
            )
