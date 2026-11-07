"""Map PyIceberg snapshots to the primitive TableCommitPage."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.adapter.outbound.table.pyiceberg.commit_writer_of import (
    commit_writer_of,
)
from context.table_maintenance.application.port.outbound.table import TableCommitPage

if TYPE_CHECKING:
    from pyiceberg.table import Table
    from pyiceberg.table.snapshots import Snapshot


def commit_page_from_table(table: Table, since: str | None, limit: int) -> TableCommitPage:
    """Build the newest-first page of commits at or after ``since``."""
    threshold_ms = _to_ms(since) if since is not None else None
    snapshots = sorted(
        (s for s in table.metadata.snapshots if threshold_ms is None or s.timestamp_ms >= threshold_ms),
        key=lambda s: (s.timestamp_ms, s.sequence_number or 0),
        reverse=True,
    )
    return TableCommitPage(
        table_uuid=str(table.metadata.table_uuid),
        commits=[_commit(s) for s in snapshots[:limit]],
        truncated=len(snapshots) > limit,
    )


def _to_ms(timestamp: str) -> int:
    parsed = datetime.fromisoformat(timestamp)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return int(parsed.timestamp() * 1000)


def _commit(snapshot: Snapshot) -> dict[str, object]:
    summary: dict[str, str] = {}
    operation: str | None = None
    if snapshot.summary is not None:
        operation = str(snapshot.summary.operation.value)
        summary = {"operation": operation, **snapshot.summary.additional_properties}
    return {
        "snapshot_id": snapshot.snapshot_id,
        "parent_id": snapshot.parent_snapshot_id,
        "committed_at": datetime.fromtimestamp(snapshot.timestamp_ms / 1000, tz=UTC).isoformat(),
        "operation": operation,
        "summary": summary,
        "writer": commit_writer_of(summary),
    }
