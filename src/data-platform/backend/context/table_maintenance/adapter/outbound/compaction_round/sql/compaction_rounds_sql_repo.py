"""Define the CompactionRoundsSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, insert, select

from context.table_maintenance.adapter.outbound.compaction_round.sql.compaction_round_row_mapper import (
    CompactionRoundRowMapper,
)
from context.table_maintenance.adapter.outbound.compaction_round.sql.compaction_rounds_table import (
    compaction_rounds_table as t,
)
from context.table_maintenance.application.port.outbound.compaction_round import CompactionRoundsRepo

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy import Engine

    from base import EntityId
    from context.table_maintenance.application.port.outbound.compaction_round import CompactionRound


class CompactionRoundsSqlRepo(CompactionRoundsRepo):
    """Store CompactionRound records in a SQL database, one row per round."""

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: CompactionRound) -> CompactionRound:
        """Insert or replace the round."""
        self.save(entity)
        return entity

    def save(self, entity: CompactionRound) -> None:
        """Replace the round's row in one transaction."""
        with self._engine.begin() as conn:
            conn.execute(delete(t).where(t.c.id == entity.id.value))
            conn.execute(insert(t).values(**CompactionRoundRowMapper.to_values(entity)))

    def get(self, entity_id: EntityId) -> CompactionRound | None:
        """Return the round with the given id, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(t).where(t.c.id == entity_id.value)).first()
        return None if row is None else CompactionRoundRowMapper.to_aggregate(row._mapping)

    def list_all(self) -> list[CompactionRound]:
        """Return every round, newest first."""
        with self._engine.connect() as conn:
            rows = conn.execute(select(t).order_by(t.c.started_at.desc(), t.c.id.desc())).all()
        return [CompactionRoundRowMapper.to_aggregate(r._mapping) for r in rows]

    def list_recent(self, *, limit: int, before: datetime | None = None) -> list[CompactionRound]:
        """Return up to ``limit`` rounds, newest first, that started strictly before ``before``."""
        stmt = select(t)
        if before is not None:
            stmt = stmt.where(t.c.started_at < before)
        stmt = stmt.order_by(t.c.started_at.desc(), t.c.id.desc()).limit(limit)
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return [CompactionRoundRowMapper.to_aggregate(r._mapping) for r in rows]

    def purge(self, *, keep: int) -> int:
        """Delete every round but the ``keep`` newest and return how many went."""
        newest = select(t.c.id).order_by(t.c.started_at.desc(), t.c.id.desc()).limit(keep)
        with self._engine.begin() as conn:
            kept = list(conn.execute(newest).scalars())
            result = conn.execute(delete(t).where(t.c.id.not_in(kept)) if kept else delete(t))
        return result.rowcount
