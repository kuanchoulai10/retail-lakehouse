"""Define the MaintenanceJobContent type."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from context.table_maintenance.application.domain.model.table_maintenance_run.expire_snapshots_job_content import (
    ExpireSnapshotsJobContent,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.remove_orphan_files_job_content import (  # noqa: E501
    RemoveOrphanFilesJobContent,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.rewrite_data_files_job_content import (
    RewriteDataFilesJobContent,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.rewrite_manifests_job_content import (
    RewriteManifestsJobContent,
)

type MaintenanceJobContent = Annotated[
    RewriteDataFilesJobContent | RewriteManifestsJobContent | ExpireSnapshotsJobContent | RemoveOrphanFilesJobContent,
    Field(discriminator="operation"),
]
"""What one job of any operation does, read by its ``operation``."""
