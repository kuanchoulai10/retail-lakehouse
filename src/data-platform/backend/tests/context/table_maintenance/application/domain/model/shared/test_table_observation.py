"""Test the TableObservation value object."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.shared import (
    ManifestStats,
    PartitionStats,
    SnapshotInfo,
    TableObservation,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _observation(*snapshots: SnapshotInfo) -> TableObservation:
    return TableObservation(
        table_uuid="u1",
        properties={},
        current_snapshot_id=None,
        specs=(),
        partitions=(),
        manifests=(),
        snapshots=snapshots,
    )


def test_a_table_without_snapshots_has_no_last_commit():
    """A table never committed to has no last commit."""
    assert _observation().last_committed_at is None


def test_the_last_commit_is_the_newest_snapshot_whatever_the_order():
    """The last commit is the newest snapshot's commit time, not the last one listed or the current one."""
    newest = T0 + timedelta(hours=2)
    observation = _observation(
        SnapshotInfo(snapshot_id=1, committed_at=T0),
        SnapshotInfo(snapshot_id=3, committed_at=newest),
        SnapshotInfo(snapshot_id=2, committed_at=T0 + timedelta(hours=1)),
    )
    assert observation.last_committed_at == newest


def test_negative_record_count_is_refused():
    """A negative record count is an invariant violation."""
    with pytest.raises(InvariantViolation):
        PartitionStats(
            spec_id=0,
            values=(),
            data_file_count=1,
            position_delete_file_count=0,
            equality_delete_file_count=0,
            total_data_file_size_bytes=10,
            data_record_count=-1,
        )


def test_negative_manifest_entry_count_is_refused():
    """A negative manifest entry count is an invariant violation."""
    with pytest.raises(InvariantViolation):
        ManifestStats(length_bytes=10, added_entries=-1)
