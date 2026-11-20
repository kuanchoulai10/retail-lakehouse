"""Test the target value objects of the four operations."""

from __future__ import annotations

from datetime import timedelta

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    AtMost,
    CompactionUnit,
    ExpireSnapshotsTarget,
    RemoveOrphanFilesTarget,
    RewriteDataFilesTarget,
    RewriteManifestsTarget,
)


def test_reducible_files_target_is_per_partition_by_default() -> None:
    """Check the compaction target compares each partition unless told otherwise."""
    target = RewriteDataFilesTarget.from_primitives({"reducible_files": {"at_most": 5}})
    assert target.per is CompactionUnit.PARTITION
    assert target.reducible_files == AtMost(at_most=5)


def test_reducible_files_target_per_table() -> None:
    """Check the compaction target can compare the whole table."""
    target = RewriteDataFilesTarget.from_primitives({"reducible_files": {"at_most": 5}, "per": "table"})
    assert target.per is CompactionUnit.TABLE


def test_at_most_zero_is_allowed_and_negative_is_refused() -> None:
    """Check the count may be zero but not below."""
    assert AtMost.from_primitives({"at_most": 0}).at_most == 0
    with pytest.raises(InvariantViolation):
        AtMost.from_primitives({"at_most": -1})


def test_small_manifests_target() -> None:
    """Check the manifest target reads its count."""
    assert RewriteManifestsTarget.from_primitives({"small_manifests": {"at_most": 3}}).small_manifests.at_most == 3


def test_expire_target_fields_are_optional() -> None:
    """Check an empty expire target holds neither value."""
    target = ExpireSnapshotsTarget.from_primitives({})
    assert target.min_snapshots_to_keep is None
    assert target.max_snapshot_age is None


def test_expire_target_reads_wire_names() -> None:
    """Check the age is read in seconds."""
    target = ExpireSnapshotsTarget.from_primitives({"min_snapshots_to_keep": 10, "max_snapshot_age_seconds": 86400})
    assert target.min_snapshots_to_keep == 10
    assert target.max_snapshot_age == timedelta(days=1)
    assert target.to_primitives() == {"min_snapshots_to_keep": 10, "max_snapshot_age_seconds": 86400}


@pytest.mark.parametrize("data", [{"min_snapshots_to_keep": 0}, {"max_snapshot_age_seconds": 0}])
def test_expire_target_refuses_non_positive(data: dict[str, int]) -> None:
    """Check retention values must be positive."""
    with pytest.raises(InvariantViolation):
        ExpireSnapshotsTarget.from_primitives(data)


def test_orphan_older_than_reads_wire_name() -> None:
    """Check the orphan age is read in seconds."""
    target = RemoveOrphanFilesTarget.from_primitives({"older_than_seconds": 259200})
    assert target.older_than == timedelta(days=3)


def test_orphan_older_than_under_a_day_is_refused() -> None:
    """Check an orphan age under a day is refused."""
    with pytest.raises(InvariantViolation, match="must be at least 1 day"):
        RemoveOrphanFilesTarget.from_primitives({"older_than_seconds": 86399})


def test_orphan_older_than_a_day_is_allowed() -> None:
    """Check exactly a day is allowed."""
    assert RemoveOrphanFilesTarget.from_primitives({"older_than_seconds": 86400}).older_than == timedelta(days=1)
