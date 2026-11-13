"""Define the InMemoryCompactionCandidatesRepo test fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.outbound.compaction_candidate import (
    CompactionCandidatesRepo,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from base import EntityId
    from context.table_maintenance.application.port.outbound.compaction_candidate import (
        CompactionCandidate,
        CompactionCandidateId,
        TableId,
        TableMaintenanceRunId,
    )


class InMemoryCompactionCandidatesRepo(CompactionCandidatesRepo):
    """Keep compaction candidates in a dict keyed by table and partition, as copies.

    Copies keep a caller's later changes out of the store, as a database would.
    """

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[tuple[str, str], CompactionCandidate] = {}
        self.saves = 0

    def create(self, entity: CompactionCandidate) -> CompactionCandidate:
        """Insert a candidate."""
        self.save_all([entity])
        return entity

    def get(self, entity_id: EntityId) -> CompactionCandidate | None:
        """Return a copy of the candidate or None."""
        found = next((c for c in self.items.values() if c.id == entity_id), None)
        return None if found is None else found.model_copy(deep=True)

    def list_all(self) -> list[CompactionCandidate]:
        """Return copies of all candidates."""
        return [c.model_copy(deep=True) for c in self.items.values()]

    def list_by_table(self, table_uuid: TableId) -> list[CompactionCandidate]:
        """Return copies of the table's candidates."""
        return [c.model_copy(deep=True) for c in self.items.values() if c.table_uuid == table_uuid]

    def list_by_run(self, run_id: TableMaintenanceRunId) -> list[CompactionCandidate]:
        """Return copies of the candidates the run holds or last held."""
        return [c.model_copy(deep=True) for c in self.items.values() if c.claimed_by_run_id == run_id]

    def save_all(self, candidates: Sequence[CompactionCandidate]) -> None:
        """Insert or replace copies of the candidates."""
        self.saves += 1
        for candidate in candidates:
            self.items[(candidate.table_uuid.value, candidate.partition.canonical())] = candidate.model_copy(deep=True)

    def delete(self, ids: Sequence[CompactionCandidateId]) -> None:
        """Delete the candidates with these ids."""
        doomed = set(ids)
        self.items = {k: c for k, c in self.items.items() if c.id not in doomed}

    def delete_by_table(self, table_uuid: TableId) -> None:
        """Delete every candidate of the table."""
        self.items = {k: c for k, c in self.items.items() if c.table_uuid != table_uuid}
