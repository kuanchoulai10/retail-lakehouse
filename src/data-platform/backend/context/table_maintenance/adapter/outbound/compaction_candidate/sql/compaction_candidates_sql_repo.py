"""Define the CompactionCandidatesSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError

from context.table_maintenance.adapter.outbound.compaction_candidate.sql.compaction_candidate_row_mapper import (
    CompactionCandidateRowMapper,
)
from context.table_maintenance.adapter.outbound.compaction_candidate.sql.compaction_candidates_table import (
    compaction_candidates_table as t,
)
from context.table_maintenance.application.port.outbound.compaction_candidate import (
    CandidateState,
    CompactionCandidatesRepo,
    StaleCompactionCandidate,
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
    row by id is replacing it by that key. Each row carries a version: a save
    inserts a candidate never stored and updates any other only where the row
    is still at the version it was read at, all in one transaction.
    """

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: CompactionCandidate) -> CompactionCandidate:
        """Store one candidate as ``save_all`` does: insert a new one, or update one still at its read version.

        Raises ``StaleCompactionCandidate`` when the row exists already (for a
        new candidate) or moved past the version it was read at.
        """
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

    def list_unheld(self) -> list[CompactionCandidate]:
        """Return every candidate of every table that is not held."""
        unheld = [s.value for s in CandidateState if s is not CandidateState.HELD]
        stmt = select(t).where(t.c.state.in_(unheld)).order_by(t.c.table_uuid, t.c.partition_key)
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return [CompactionCandidateRowMapper.to_aggregate(r._mapping) for r in rows]

    def save_all(self, candidates: Sequence[CompactionCandidate]) -> None:
        """Store the candidates in one transaction, checking each row's version; a stale one rolls all back.

        Stored candidates are updated in id order, so two writers that share
        rows lock them in the same order and do not deadlock. New candidates are
        inserted in chunks that keep each statement small; a row that exists
        already means another writer created it first.
        """
        if not candidates:
            return
        new = [CompactionCandidateRowMapper.to_values(c) | {"version": 1} for c in candidates if c.version == 0]
        stored = sorted((c for c in candidates if c.version > 0), key=lambda c: c.id.value)
        try:
            with self._engine.begin() as conn:
                for candidate in stored:
                    values = CompactionCandidateRowMapper.to_values(candidate)
                    result = conn.execute(
                        update(t)
                        .where(t.c.id == candidate.id.value, t.c.version == candidate.version)
                        .values(**values, version=candidate.version + 1)
                    )
                    if result.rowcount != 1:
                        raise StaleCompactionCandidate(
                            f"candidate {candidate.label} of table {candidate.table_uuid.value} changed since "
                            f"version {candidate.version} was read"
                        )
                for start in range(0, len(new), _CHUNK):
                    conn.execute(insert(t), new[start : start + _CHUNK])
        except IntegrityError as error:
            raise StaleCompactionCandidate(f"a candidate was created by another writer first: {error}") from error
        for candidate in candidates:
            candidate.mark_saved()

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
