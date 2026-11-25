"""Test the content of a maintenance job: what one run of each operation does."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
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
    maintenance_job_content_from_primitives,
)

TAIPEI = timezone(timedelta(hours=8))
OLDER_THAN = datetime(2026, 10, 22, 20, 15, 30, 123456, tzinfo=TAIPEI)


def _region(spec_id):
    field = PartitionFieldInfo(
        field_id=1000, name="region", source_column="region", source_type="string", transform="identity"
    )
    return SpecPartitions(spec=PartitionSpecInfo(spec_id=spec_id, fields=(field,)), values=(("eu",),))


CONTENTS = [
    RewriteDataFilesJobContent(
        target_file_size_bytes=536870912,
        options=RewriteDataFilesOptions(strategy=RewriteDataFilesStrategy.SORT, sort_order="id", min_input_files=2),
        partitions=(_region(0), _region(1)),
    ),
    RewriteDataFilesJobContent(target_file_size_bytes=1),
    RewriteManifestsJobContent(options=RewriteManifestsOptions(use_caching=False)),
    RewriteManifestsJobContent(),
    ExpireSnapshotsJobContent(
        older_than=OLDER_THAN,
        retain_last=3,
        options=ExpireSnapshotsOptions(max_concurrent_deletes=4, stream_results=True),
    ),
    RemoveOrphanFilesJobContent(
        older_than=OLDER_THAN,
        options=RemoveOrphanFilesOptions(prefix_mismatch_mode=PrefixMismatchMode.IGNORE),
    ),
]


@pytest.mark.parametrize("content", CONTENTS, ids=lambda content: f"{content.operation.value}")
def test_content_round_trips_through_primitives(content):
    """Stored or sent as JSON, a job's content reads back equal, the time zone and microseconds included."""
    assert maintenance_job_content_from_primitives(content.to_primitives()) == content


def test_each_content_names_its_operation():
    """The operation is fixed by the kind of content."""
    assert [content.operation for content in CONTENTS] == [
        MaintenanceOperation.REWRITE_DATA_FILES,
        MaintenanceOperation.REWRITE_DATA_FILES,
        MaintenanceOperation.REWRITE_MANIFESTS,
        MaintenanceOperation.REWRITE_MANIFESTS,
        MaintenanceOperation.EXPIRE_SNAPSHOTS,
        MaintenanceOperation.REMOVE_ORPHAN_FILES,
    ]


def test_primitives_leave_unset_options_out():
    """Only the options a policy sets are written down."""
    assert RewriteDataFilesJobContent(target_file_size_bytes=10).to_primitives() == {
        "operation": "rewrite_data_files",
        "target_file_size_bytes": 10,
        "options": {},
        "partitions": [],
    }
    assert ExpireSnapshotsJobContent(older_than=OLDER_THAN, retain_last=1).to_primitives() == {
        "operation": "expire_snapshots",
        "older_than": "2026-10-22T20:15:30.123456+08:00",
        "retain_last": 1,
        "options": {},
    }


@pytest.mark.parametrize("kind", [ExpireSnapshotsJobContent, RemoveOrphanFilesJobContent])
def test_older_than_must_be_an_aware_time(kind):
    """A time without a zone names no instant, so no job is built from it."""
    extra = {"retain_last": 1} if kind is ExpireSnapshotsJobContent else {}
    with pytest.raises(InvariantViolation, match="timezone"):
        kind(older_than=datetime(2026, 10, 22), **extra)  # noqa: DTZ001


def test_a_compaction_selects_each_spec_once():
    """Two selections of one spec would be two scopes for the same partitions."""
    with pytest.raises(InvariantViolation, match="spec 0 is selected twice"):
        RewriteDataFilesJobContent(target_file_size_bytes=1, partitions=(_region(0), _region(0)))


def test_a_compaction_lists_its_specs_in_order():
    """The selections are kept by spec id, so a content has one written form."""
    with pytest.raises(InvariantViolation, match="sorted by spec id"):
        RewriteDataFilesJobContent(target_file_size_bytes=1, partitions=(_region(1), _region(0)))


@pytest.mark.parametrize("field", ["target_file_size_bytes", "retain_last"])
def test_sizes_and_counts_are_positive(field):
    """A target size or a number of snapshots to keep of zero is no setting."""
    with pytest.raises(InvariantViolation):
        if field == "target_file_size_bytes":
            RewriteDataFilesJobContent(target_file_size_bytes=0)
        else:
            ExpireSnapshotsJobContent(older_than=datetime(2026, 1, 1, tzinfo=UTC), retain_last=0)


@pytest.mark.parametrize(
    "data",
    [{}, {"operation": "vacuum"}, {"operation": 1}],
    ids=["missing", "unknown", "not text"],
)
def test_primitives_without_a_known_operation_are_refused(data):
    """Content is read by its operation, so one without a known operation cannot be read."""
    with pytest.raises(ValueError, match="operation"):
        maintenance_job_content_from_primitives(data)


def test_primitives_of_one_operation_are_not_read_as_another():
    """The fields of each content are its own; a mix is refused."""
    with pytest.raises(InvariantViolation):
        maintenance_job_content_from_primitives({"operation": "rewrite_manifests", "retain_last": 1})
