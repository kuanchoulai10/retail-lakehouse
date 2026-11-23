"""Test the where clauses the Spark adapter sends for a job."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s import spark_where_clauses
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    ExpireSnapshotsJob,
    JobPartitionField,
    JobPartitionSpec,
    RemoveOrphanFilesJob,
    RewriteDataFilesJob,
    RewriteManifestsJob,
)

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)
REGION = (JobPartitionField(source_column="region", source_type="string", transform="identity"),)
BUCKET = (JobPartitionField(source_column="id", source_type="long", transform="bucket[8]"),)


def test_one_where_clause_per_spec():
    """A compaction scoped to partitions sends one where clause per spec, in the job's spec order."""
    job = RewriteDataFilesJob(
        target_file_size_bytes=1,
        partitions=(
            JobPartitionSpec(spec_id=0, fields=REGION, values=(("us",), ("eu",))),
            JobPartitionSpec(spec_id=1, fields=BUCKET, values=((2,),)),
        ),
    )
    assert spark_where_clauses("iceberg", job) == [
        "(`region` = 'eu') OR (`region` = 'us')",
        "(`iceberg`.system.bucket(8, `id`) = 2)",
    ]


def test_where_clauses_follow_spec_id_whatever_order_the_job_lists_them():
    """A job that lists its specs out of order still sends the where clauses by spec id, as the runtime expects."""
    job = RewriteDataFilesJob(
        target_file_size_bytes=1,
        partitions=(
            JobPartitionSpec(spec_id=1, fields=BUCKET, values=((2,),)),
            JobPartitionSpec(spec_id=0, fields=REGION, values=(("eu",),)),
        ),
    )
    assert spark_where_clauses("iceberg", job) == [
        "(`region` = 'eu')",
        "(`iceberg`.system.bucket(8, `id`) = 2)",
    ]


@pytest.mark.parametrize(
    "job",
    [
        RewriteDataFilesJob(target_file_size_bytes=1),
        RewriteManifestsJob(),
        ExpireSnapshotsJob(older_than=NOW, retain_last=1),
        RemoveOrphanFilesJob(older_than=NOW),
    ],
    ids=["whole-table compaction", "manifests", "expiry", "orphans"],
)
def test_a_job_without_partitions_has_no_where_clause(job):
    """No where clause means the whole table."""
    assert spark_where_clauses("iceberg", job) == []
