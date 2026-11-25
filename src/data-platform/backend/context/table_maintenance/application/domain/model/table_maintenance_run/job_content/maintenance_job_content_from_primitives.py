"""Define the maintenance_job_content_from_primitives function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table_maintenance_run.job_content.expire_snapshots_job_content import (  # noqa: E501
    ExpireSnapshotsJobContent,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.job_content.remove_orphan_files_job_content import (  # noqa: E501
    RemoveOrphanFilesJobContent,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.job_content.rewrite_data_files_job_content import (  # noqa: E501
    RewriteDataFilesJobContent,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.job_content.rewrite_manifests_job_content import (  # noqa: E501
    RewriteManifestsJobContent,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from context.table_maintenance.application.domain.model.table_maintenance_run.job_content.maintenance_job_content import (  # noqa: E501
        MaintenanceJobContent,
    )

_KINDS: dict[MaintenanceOperation, type[MaintenanceJobContent]] = {
    MaintenanceOperation.REWRITE_DATA_FILES: RewriteDataFilesJobContent,
    MaintenanceOperation.REWRITE_MANIFESTS: RewriteManifestsJobContent,
    MaintenanceOperation.EXPIRE_SNAPSHOTS: ExpireSnapshotsJobContent,
    MaintenanceOperation.REMOVE_ORPHAN_FILES: RemoveOrphanFilesJobContent,
}


def maintenance_job_content_from_primitives(data: Mapping[str, Any]) -> MaintenanceJobContent:
    """Read the content of a job from JSON primitives, as the kind its ``operation`` names.

    Raises ``ValueError`` when ``operation`` is missing or names no operation, and ``InvariantViolation``
    when the rest does not fit that kind.
    """
    operation = data.get("operation")
    if not isinstance(operation, str) or operation not in MaintenanceOperation:
        raise ValueError(f"job content needs a known operation, got {operation!r}")
    return _KINDS[MaintenanceOperation(operation)].from_primitives(dict(data))
