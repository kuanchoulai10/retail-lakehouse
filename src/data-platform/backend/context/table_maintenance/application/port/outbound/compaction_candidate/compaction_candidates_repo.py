"""Define the CompactionCandidatesRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Repository
from context.table_maintenance.application.domain.model.compaction_candidate import (
    CompactionCandidate,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from context.table_maintenance.application.domain.model.compaction_candidate import (
        CompactionCandidateId,
    )
    from context.table_maintenance.application.domain.model.table import TableId
    from context.table_maintenance.application.domain.model.table_maintenance_run import (
        TableMaintenanceRunId,
    )


class CompactionCandidatesRepo(Repository[CompactionCandidate]):
    """Persist and query CompactionCandidate aggregates, one per table and partition."""

    @abstractmethod
    def list_by_table(self, table_uuid: TableId) -> list[CompactionCandidate]:
        """Return every candidate of the table, in no particular order."""

    @abstractmethod
    def list_by_run(self, run_id: TableMaintenanceRunId) -> list[CompactionCandidate]:
        """Return the candidates the run holds or last held."""

    @abstractmethod
    def list_pending(self) -> list[CompactionCandidate]:
        """Return every pending candidate of every table, in no particular order."""

    @abstractmethod
    def save_all(self, candidates: Sequence[CompactionCandidate]) -> None:
        """Store each candidate, all or none, keyed by its table and partition.

        A candidate never stored (version 0) is inserted; any other replaces its
        row only if the row is still at the version it was read at. If one row
        was stored meanwhile (by another writer), nothing is stored and
        ``StaleCompactionCandidate`` is raised; the caller reads again and
        retries. Each candidate saved takes its new version (``mark_saved``).
        """

    @abstractmethod
    def delete(self, ids: Sequence[CompactionCandidateId]) -> None:
        """Delete the candidates with these ids; unknown ids are ignored."""

    @abstractmethod
    def delete_by_table(self, table_uuid: TableId) -> None:
        """Delete every candidate of the table."""
