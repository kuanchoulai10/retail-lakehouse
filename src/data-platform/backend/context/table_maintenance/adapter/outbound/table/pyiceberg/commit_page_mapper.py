"""Map PyIceberg snapshots to the primitive TableCommitPage."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.adapter.outbound.table.pyiceberg.commit_writer_of import (
    commit_writer_of,
)
from context.table_maintenance.application.port.outbound.table import (
    TableCommitPage,
    TableCommitSelection,
)

if TYPE_CHECKING:
    from pyiceberg.table import Table
    from pyiceberg.table.snapshots import Snapshot


def commit_page_from_table(table: Table, selection: TableCommitSelection) -> TableCommitPage:
    """Build the newest-first page of the commits ``selection`` keeps, cut at its limit."""
    since_ms = None if selection.since is None else _to_ms(selection.since)
    before_ms = None if selection.before is None else _to_ms(selection.before)
    snapshots = sorted(
        (
            s
            for s in table.metadata.snapshots
            if (since_ms is None or s.timestamp_ms >= since_ms) and (before_ms is None or s.timestamp_ms < before_ms)
        ),
        key=lambda s: (s.timestamp_ms, s.sequence_number or 0),
        reverse=True,
    )
    commits = [_commit(s) for s in snapshots]
    if selection.writer is not None:
        commits = [c for c in commits if c["writer"] == selection.writer]
    return TableCommitPage(
        table_uuid=str(table.metadata.table_uuid),
        commits=commits[: selection.limit],
        truncated=len(commits) > selection.limit,
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
