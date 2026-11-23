"""Define the job_content helper."""

from __future__ import annotations

from datetime import UTC, datetime

from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    ExpireSnapshotsJobContent,
    MaintenanceJobContent,
    RemoveOrphanFilesJobContent,
    RewriteDataFilesJobContent,
    RewriteManifestsJobContent,
)

OLDER_THAN = datetime(2026, 10, 23, tzinfo=UTC)


def job_content(operation: MaintenanceOperation | str) -> MaintenanceJobContent:
    """Return a plain content of ``operation``: a whole-table compaction, no options, fixed ages."""
    match MaintenanceOperation(operation):
        case MaintenanceOperation.REWRITE_DATA_FILES:
            return RewriteDataFilesJobContent(target_file_size_bytes=536870912)
        case MaintenanceOperation.REWRITE_MANIFESTS:
            return RewriteManifestsJobContent()
        case MaintenanceOperation.EXPIRE_SNAPSHOTS:
            return ExpireSnapshotsJobContent(older_than=OLDER_THAN, retain_last=1)
        case MaintenanceOperation.REMOVE_ORPHAN_FILES:
            return RemoveOrphanFilesJobContent(older_than=OLDER_THAN)
