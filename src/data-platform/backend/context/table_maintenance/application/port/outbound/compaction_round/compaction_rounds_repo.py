"""Define the CompactionRoundsRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Repository
from context.table_maintenance.application.domain.model.compaction_round import CompactionRound

if TYPE_CHECKING:
    from datetime import datetime


class CompactionRoundsRepo(Repository[CompactionRound]):
    """Persist and query CompactionRound records."""

    @abstractmethod
    def save(self, entity: CompactionRound) -> None:
        """Insert the round, or replace the one stored under its id."""

    @abstractmethod
    def list_recent(self, *, limit: int, before: datetime | None = None) -> list[CompactionRound]:
        """Return up to ``limit`` rounds, newest first, that started strictly before ``before``."""

    @abstractmethod
    def purge(self, *, keep: int) -> int:
        """Delete every round but the ``keep`` newest and return how many went."""
