"""Define the EventOutboxSqlRepo adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import insert, select, update

from core.adapter.outbound.sql.outbox_table import outbox_table
from core.application.domain.model.outbox_entry import OutboxEntry
from core.application.port.outbound.event_outbox_repo import EventOutboxRepo

if TYPE_CHECKING:
    from sqlalchemy import Engine


class EventOutboxSqlRepo(EventOutboxRepo):
    """EventOutboxRepo backed by a SQLAlchemy Engine."""

    def __init__(self, engine: Engine) -> None:
        """Initialize with a SQLAlchemy engine."""
        self._engine = engine

    def save(self, entries: list[OutboxEntry]) -> None:
        """Insert outbox entries."""
        if not entries:
            return
        with self._engine.begin() as conn:
            for entry in entries:
                conn.execute(
                    insert(outbox_table).values(
                        id=entry.id,
                        aggregate_type=entry.aggregate_type,
                        aggregate_id=entry.aggregate_id,
                        event_type=entry.event_type,
                        payload=entry.payload,
                        occurred_at=entry.occurred_at,
                        published_at=entry.published_at,
                    )
                )

    def fetch_unpublished(self, batch_size: int = 100) -> list[OutboxEntry]:
        """Return unpublished entries ordered by occurred_at."""
        stmt = (
            select(outbox_table)
            .where(outbox_table.c.published_at.is_(None))
            .order_by(outbox_table.c.occurred_at)
            .limit(batch_size)
        )
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [
            OutboxEntry(
                id=row["id"],
                aggregate_type=row["aggregate_type"],
                aggregate_id=row["aggregate_id"],
                event_type=row["event_type"],
                payload=row["payload"],
                occurred_at=row["occurred_at"],
                published_at=row["published_at"],
            )
            for row in rows
        ]

    def mark_published(self, entry_ids: list[str]) -> None:
        """Set published_at for the given IDs."""
        if not entry_ids:
            return
        stmt = (
            update(outbox_table)
            .where(outbox_table.c.id.in_(entry_ids))
            .values(published_at=datetime.now(UTC))
        )
        with self._engine.begin() as conn:
            conn.execute(stmt)
