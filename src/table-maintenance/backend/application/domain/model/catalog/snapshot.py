"""Define the Snapshot value object."""

from __future__ import annotations

from dataclasses import dataclass

from core.base.value_object import ValueObject
from application.domain.model.catalog.snapshot_summary import SnapshotSummary


@dataclass(frozen=True)
class Snapshot(ValueObject):
    """An immutable point-in-time snapshot of a table."""

    snapshot_id: int
    parent_id: int | None
    timestamp_ms: int
    summary: SnapshotSummary
