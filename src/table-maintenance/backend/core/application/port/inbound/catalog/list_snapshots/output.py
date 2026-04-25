"""Define the ListSnapshotsOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListSnapshotsOutputItem:
    """A single snapshot in the result."""

    snapshot_id: int
    parent_id: int | None
    timestamp_ms: int
    summary: dict[str, str]


@dataclass(frozen=True)
class ListSnapshotsOutput:
    """Output for the ListSnapshots use case."""

    snapshots: list[ListSnapshotsOutputItem]
