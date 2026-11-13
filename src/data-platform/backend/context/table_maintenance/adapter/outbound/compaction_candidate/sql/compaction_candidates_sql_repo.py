"""Define the CompactionCandidatesSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, insert, select

from context.table_maintenance.adapter.outbound.compaction_candidate.sql.compaction_candidate_row_mapper import (
    CompactionCandidateRowMapper,
)
from context.table_maintenance.adapter.outbound.compaction_candidate.sql.compaction_candidates_table import (
    compaction_candidates_table as t,
)
from context.table_maintenance.application.port.outbound.compaction_candidate import (
    CompactionCandidatesRepo,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy import Engine

    from base import EntityId
    from context.table_maintenance.application.port.outbound.compaction_candidate import (
        CompactionCandidate,
        CompactionCandidateId,
        TableId,
        TableMaintenanceRunId,
    )


_CHUNK = 500


class CompactionCandidatesSqlRepo(CompactionCandidatesRepo):
    """Store CompactionCandidate aggregates in a SQL database, one row per table and partition.

    A candidate's id is derived from its table and partition, so replacing the
    row by id is replacing it by that key.
    """

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: CompactionCandidate) -> CompactionCandidate:
        """Insert or replace one candidate."""
        self.save_all([entity])
        return entity

    def get(self, entity_id: EntityId) -> CompactionCandidate | None:
        """Return the candidate with the given id, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(t).where(t.c.id == entity_id.value)).first()
        return None if row is None else CompactionCandidateRowMapper.to_aggregate(row._mapping)

    def list_all(self) -> list[CompactionCandidate]:
        """Return every candidate."""
        with self._engine.connect() as conn:
            rows = conn.execute(select(t).order_by(t.c.table_uuid, t.c.partition_key)).all()
        return [CompactionCandidateRowMapper.to_aggregate(r._mapping) for r in rows]

    def list_by_table(self, table_uuid: TableId) -> list[CompactionCandidate]:
        """Return every candidate of the table."""
        stmt = select(t).where(t.c.table_uuid == table_uuid.value).order_by(t.c.partition_key)
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return [CompactionCandidateRowMapper.to_aggregate(r._mapping) for r in rows]

    def list_by_run(self, run_id: TableMaintenanceRunId) -> list[CompactionCandidate]:
        """Return the candidates the run holds or last held."""
        stmt = select(t).where(t.c.claimed_by_run_id == run_id.value).order_by(t.c.partition_key)
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return [CompactionCandidateRowMapper.to_aggregate(r._mapping) for r in rows]

    def save_all(self, candidates: Sequence[CompactionCandidate]) -> None:
        """Replace the rows of the candidates in one transaction, in chunks that keep each statement small."""
        if not candidates:
            return
        values = [CompactionCandidateRowMapper.to_values(c) for c in candidates]
        with self._engine.begin() as conn:
            for start in range(0, len(values), _CHUNK):
                chunk = values[start : start + _CHUNK]
                conn.execute(delete(t).where(t.c.id.in_([v["id"] for v in chunk])))
                conn.execute(insert(t), chunk)

    def delete(self, ids: Sequence[CompactionCandidateId]) -> None:
        """Delete the candidates with these ids, in chunks."""
        keys = [i.value for i in ids]
        if not keys:
            return
        with self._engine.begin() as conn:
            for start in range(0, len(keys), _CHUNK):
                conn.execute(delete(t).where(t.c.id.in_(keys[start : start + _CHUNK])))

    def delete_by_table(self, table_uuid: TableId) -> None:
        """Delete every candidate of the table."""
        with self._engine.begin() as conn:
            conn.execute(delete(t).where(t.c.table_uuid == table_uuid.value))
