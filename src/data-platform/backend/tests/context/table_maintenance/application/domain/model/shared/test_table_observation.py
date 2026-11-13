"""Test the TableObservation value object."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from context.table_maintenance.application.domain.model.shared import SnapshotInfo, TableObservation

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
