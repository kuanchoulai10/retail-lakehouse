"""Define the SubmitMaintenanceJobGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run.submit_maintenance_job.expire_snapshots_job import (  # noqa: E501
        ExpireSnapshotsJob,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_run.submit_maintenance_job.remove_orphan_files_job import (  # noqa: E501
        RemoveOrphanFilesJob,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_run.submit_maintenance_job.rewrite_data_files_job import (  # noqa: E501
        RewriteDataFilesJob,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_run.submit_maintenance_job.rewrite_manifests_job import (  # noqa: E501
        RewriteManifestsJob,
    )


@dataclass(frozen=True)
class SubmitMaintenanceJobGatewayInput:
    """Carry what a maintenance job does on one table, and how it reports and is scheduled.

    ``job`` holds the operation's settings, and the adapter writes them as the engine's call.
    """

    run_id: str
    operation: str
    attempt: int
    catalog: str
    namespace: str
    table: str
    job: RewriteDataFilesJob | RewriteManifestsJob | ExpireSnapshotsJob | RemoveOrphanFilesJob
    result_report_url: str
    size: str = "S"
    priority: str = "P3"
