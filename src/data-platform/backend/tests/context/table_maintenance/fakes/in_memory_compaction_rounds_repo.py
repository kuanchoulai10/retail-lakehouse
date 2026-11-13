"""Define the InMemoryCompactionRoundsRepo test fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.outbound.compaction_round import CompactionRoundsRepo

if TYPE_CHECKING:
    from datetime import datetime

    from base import EntityId
    from context.table_maintenance.application.port.outbound.compaction_round import CompactionRound


class InMemoryCompactionRoundsRepo(CompactionRoundsRepo):
    """Keep compaction rounds in a dict keyed by id; rounds are immutable once planned, so no copies are needed."""

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, CompactionRound] = {}

    def create(self, entity: CompactionRound) -> CompactionRound:
        """Insert or replace the round."""
        self.save(entity)
        return entity

    def save(self, entity: CompactionRound) -> None:
        """Insert or replace the round."""
        self.items[entity.id.value] = entity

    def get(self, entity_id: EntityId) -> CompactionRound | None:
        """Return the round or None."""
        return self.items.get(entity_id.value)

    def list_all(self) -> list[CompactionRound]:
        """Return every round, newest first."""
        return self._newest_first(self.items.values())

    def list_recent(self, *, limit: int, before: datetime | None = None) -> list[CompactionRound]:
        """Return up to ``limit`` rounds, newest first, that started strictly before ``before``."""
        rounds = [r for r in self.items.values() if before is None or r.started_at < before]
        return self._newest_first(rounds)[:limit]

    def purge(self, *, keep: int) -> int:
        """Delete every round but the ``keep`` newest."""
        kept = {r.id.value for r in self._newest_first(self.items.values())[:keep]}
        gone = len(self.items) - len(kept)
        self.items = {k: r for k, r in self.items.items() if k in kept}
        return gone

    @staticmethod
    def _newest_first(rounds) -> list[CompactionRound]:  # noqa: ANN001
        return sorted(rounds, key=lambda r: (r.started_at, r.id.value), reverse=True)
