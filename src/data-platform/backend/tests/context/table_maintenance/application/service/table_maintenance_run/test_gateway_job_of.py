"""Test the job the submit port is given for a run's content."""

from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime, timedelta, timezone

import pytest

from context.table_maintenance.application.domain.model.shared import (
    PartitionFieldInfo,
    PartitionSpecInfo,
    SpecPartitions,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    ExpireSnapshotsOptions,
    PrefixMismatchMode,
    RemoveOrphanFilesOptions,
    RewriteDataFilesOptions,
    RewriteDataFilesStrategy,
    RewriteManifestsOptions,
)
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
from context.table_maintenance.application.service.table_maintenance_run import gateway_job_of

OLDER_THAN = datetime(2026, 10, 22, 20, tzinfo=timezone(timedelta(hours=8)))


def test_a_compaction_job_carries_its_size_options_and_partitions():
    """Every setting and partition of a compaction reaches the port, enums as their text."""
    day = PartitionFieldInfo(
        field_id=1000, name="ts_day", source_column="ts", source_type="timestamptz", transform="day"
    )
    content = RewriteDataFilesJobContent(
        target_file_size_bytes=100,
        options=RewriteDataFilesOptions(
            strategy=RewriteDataFilesStrategy.SORT,
            sort_order="id",
            min_input_files=2,
            partial_progress_enabled=True,
            partial_progress_max_commits=3,
            max_concurrent_file_group_rewrites=4,
            rewrite_all=False,
            delete_file_threshold=5,
            remove_dangling_deletes=True,
            max_file_group_size_bytes=6,
        ),
        partitions=(SpecPartitions(spec=PartitionSpecInfo(spec_id=1, fields=(day,)), values=((20385,), (None,))),),
    )
    assert gateway_job_of(content) == RewriteDataFilesJob(
        target_file_size_bytes=100,
        partitions=(
            JobPartitionSpec(
                spec_id=1,
                fields=(JobPartitionField(source_column="ts", source_type="timestamptz", transform="day"),),
                values=((20385,), (None,)),
            ),
        ),
        strategy="sort",
        sort_order="id",
        min_input_files=2,
        partial_progress_enabled=True,
        partial_progress_max_commits=3,
        max_concurrent_file_group_rewrites=4,
        rewrite_all=False,
        delete_file_threshold=5,
        remove_dangling_deletes=True,
        max_file_group_size_bytes=6,
    )


def test_unset_options_stay_unset():
    """An option the policy leaves out is left to the procedure."""
    assert gateway_job_of(RewriteDataFilesJobContent(target_file_size_bytes=1)) == RewriteDataFilesJob(
        target_file_size_bytes=1
    )
    assert gateway_job_of(RewriteManifestsJobContent()) == RewriteManifestsJob()


def test_the_other_jobs_carry_their_settings():
    """Manifests, expiry and orphan removal reach the port with their ages, counts and options."""
    assert gateway_job_of(
        RewriteManifestsJobContent(options=RewriteManifestsOptions(use_caching=False))
    ) == RewriteManifestsJob(use_caching=False)
    assert gateway_job_of(
        ExpireSnapshotsJobContent(
            older_than=OLDER_THAN,
            retain_last=3,
            options=ExpireSnapshotsOptions(max_concurrent_deletes=8, stream_results=True),
        )
    ) == ExpireSnapshotsJob(older_than=OLDER_THAN, retain_last=3, max_concurrent_deletes=8, stream_results=True)
    assert gateway_job_of(
        RemoveOrphanFilesJobContent(
            older_than=OLDER_THAN,
            options=RemoveOrphanFilesOptions(max_concurrent_deletes=4, prefix_mismatch_mode=PrefixMismatchMode.IGNORE),
        )
    ) == RemoveOrphanFilesJob(older_than=OLDER_THAN, max_concurrent_deletes=4, prefix_mismatch_mode="IGNORE")


def test_the_time_reaches_the_port_as_the_same_instant():
    """The port gets a time, not text, and the instant is unchanged."""
    job = gateway_job_of(RemoveOrphanFilesJobContent(older_than=OLDER_THAN))
    assert isinstance(job, RemoveOrphanFilesJob)
    assert job.older_than == datetime(2026, 10, 22, 12, tzinfo=UTC)


@pytest.mark.parametrize(
    ("options", "job"),
    [
        (RewriteDataFilesOptions, RewriteDataFilesJob),
        (RewriteManifestsOptions, RewriteManifestsJob),
        (ExpireSnapshotsOptions, ExpireSnapshotsJob),
        (RemoveOrphanFilesOptions, RemoveOrphanFilesJob),
    ],
)
def test_every_option_has_a_field_on_its_job(options, job):
    """An option added to a policy has a place on the job the adapter writes, under the same name."""
    assert set(options.model_fields) <= {field.name for field in fields(job)}
