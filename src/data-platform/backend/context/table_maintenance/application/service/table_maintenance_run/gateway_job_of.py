"""Define the gateway_job_of function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_run import (
    ExpireSnapshotsJobContent,
    RemoveOrphanFilesJobContent,
    RewriteDataFilesJobContent,
    RewriteManifestsJobContent,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ExpireSnapshotsJob,
    JobPartitionField,
    JobPartitionSpec,
    RemoveOrphanFilesJob,
    RewriteDataFilesJob,
    RewriteManifestsJob,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.shared import SpecPartitions
    from context.table_maintenance.application.domain.model.table_maintenance_run import MaintenanceJobContent


def gateway_job_of(
    content: MaintenanceJobContent,
) -> RewriteDataFilesJob | RewriteManifestsJob | ExpireSnapshotsJob | RemoveOrphanFilesJob:
    """Return the job the submit port takes for ``content``: its settings, options left unset left out."""
    options = content.options.to_primitives()
    match content:
        case RewriteDataFilesJobContent():
            return RewriteDataFilesJob(
                target_file_size_bytes=content.target_file_size_bytes,
                partitions=tuple(_job_partitions(selection) for selection in content.partitions),
                **options,
            )
        case RewriteManifestsJobContent():
            return RewriteManifestsJob(**options)
        case ExpireSnapshotsJobContent():
            return ExpireSnapshotsJob(older_than=content.older_than, retain_last=content.retain_last, **options)
        case RemoveOrphanFilesJobContent():
            return RemoveOrphanFilesJob(older_than=content.older_than, **options)


def _job_partitions(selection: SpecPartitions) -> JobPartitionSpec:
    return JobPartitionSpec(
        spec_id=selection.spec.spec_id,
        fields=tuple(
            JobPartitionField(
                source_column=field.source_column, source_type=field.source_type, transform=field.transform
            )
            for field in selection.spec.fields
        ),
        values=selection.values,
    )
