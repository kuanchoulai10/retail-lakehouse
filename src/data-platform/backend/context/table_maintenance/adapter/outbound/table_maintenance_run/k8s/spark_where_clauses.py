"""Write the where clauses a maintenance job sends to Spark."""

from __future__ import annotations

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.spark_partition_where import (
    spark_partition_where,
)
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ExpireSnapshotsJob,
    RemoveOrphanFilesJob,
    RewriteDataFilesJob,
    RewriteManifestsJob,
)


def spark_where_clauses(
    catalog: str, job: RewriteDataFilesJob | RewriteManifestsJob | ExpireSnapshotsJob | RemoveOrphanFilesJob
) -> list[str]:
    """Return one where clause per partition spec of a scoped compaction, by spec id; none means the whole table."""
    if not isinstance(job, RewriteDataFilesJob):
        return []
    return [spark_partition_where(catalog, spec) for spec in sorted(job.partitions, key=lambda spec: spec.spec_id)]
