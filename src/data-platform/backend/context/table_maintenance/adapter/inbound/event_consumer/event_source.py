"""Define the EventSource port of the consumer loop."""

from __future__ import annotations

from abc import ABC, abstractmethod

from context.table_maintenance.adapter.inbound.event_consumer.event_record import (
    EventRecord,
)


class EventSource(ABC):
    """Deliver event records and accept commits once they are handled."""

    @abstractmethod
    def poll(self, timeout: float) -> EventRecord | None:
        """Return the next record, or None when none arrives within timeout seconds."""

    @abstractmethod
    def commit(self, record: EventRecord) -> None:
        """Mark the record as handled so it is not redelivered."""

    @abstractmethod
    def close(self) -> None:
        """Release the underlying connection."""
