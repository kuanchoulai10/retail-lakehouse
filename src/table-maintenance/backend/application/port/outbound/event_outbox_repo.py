"""Define the EventOutboxRepo port interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.domain.model.outbox_entry import OutboxEntry


class EventOutboxRepo(ABC):
    """Port for persisting and retrieving outbox entries."""

    @abstractmethod
    def save(self, entries: list[OutboxEntry]) -> None:
        """Persist outbox entries within the current transaction."""
        ...

    @abstractmethod
    def fetch_unpublished(self, batch_size: int = 100) -> list[OutboxEntry]:
        """Return up to batch_size unpublished entries ordered by occurred_at."""
        ...

    @abstractmethod
    def mark_published(self, entry_ids: list[str]) -> None:
        """Set published_at = now for the given entry IDs."""
        ...
