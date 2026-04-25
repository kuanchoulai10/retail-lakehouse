"""Test the Snapshot and SnapshotSummary value objects."""

from __future__ import annotations

from core.base import ValueObject
from core.application.domain.model.catalog.snapshot import Snapshot
from core.application.domain.model.catalog.snapshot_summary import SnapshotSummary


def test_snapshot_summary_is_value_object():
    """SnapshotSummary extends ValueObject."""
    assert issubclass(SnapshotSummary, ValueObject)


def test_snapshot_summary_stores_data():
    """SnapshotSummary stores raw key-value data."""
    s = SnapshotSummary(data={"operation": "append", "added-records": "5"})
    assert s.data["operation"] == "append"
    assert s.data["added-records"] == "5"


def test_snapshot_is_value_object():
    """Snapshot extends ValueObject."""
    assert issubclass(Snapshot, ValueObject)


def test_snapshot_fields():
    """Snapshot stores all fields correctly."""
    summary = SnapshotSummary(data={"operation": "append"})
    snap = Snapshot(
        snapshot_id=100, parent_id=99, timestamp_ms=1234567890, summary=summary
    )
    assert snap.snapshot_id == 100
    assert snap.parent_id == 99
    assert snap.timestamp_ms == 1234567890
    assert snap.summary == summary


def test_snapshot_parent_id_optional():
    """Root snapshot has no parent."""
    summary = SnapshotSummary(data={})
    snap = Snapshot(snapshot_id=1, parent_id=None, timestamp_ms=0, summary=summary)
    assert snap.parent_id is None


def test_snapshot_equality():
    """Two snapshots with identical fields are equal."""
    s = SnapshotSummary(data={})
    a = Snapshot(snapshot_id=1, parent_id=None, timestamp_ms=0, summary=s)
    b = Snapshot(snapshot_id=1, parent_id=None, timestamp_ms=0, summary=s)
    assert a == b
