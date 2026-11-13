"""Define the last_commit_of function."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import TableMetadata


def last_commit_of(found: TableMetadata) -> datetime | None:
    """Return the table's newest commit time as an aware UTC datetime, or None when it has none.

    A malformed time raises ``ValueError``.
    """
    if found.last_committed_at is None:
        return None
    moment = datetime.fromisoformat(found.last_committed_at)
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)
