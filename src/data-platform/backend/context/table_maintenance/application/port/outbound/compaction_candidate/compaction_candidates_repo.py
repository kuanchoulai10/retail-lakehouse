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
    def save_all(self, candidates: Sequence[CompactionCandidate]) -> None:
        """Insert or replace each candidate, keyed by its table and partition."""

    @abstractmethod
    def delete(self, ids: Sequence[CompactionCandidateId]) -> None:
        """Delete the candidates with these ids; unknown ids are ignored."""

    @abstractmethod
    def delete_by_table(self, table_uuid: TableId) -> None:
        """Delete every candidate of the table."""
