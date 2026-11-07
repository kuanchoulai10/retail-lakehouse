"""Provide an in-memory EventSource that records commits."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.adapter.inbound.event_consumer import (
    EventRecord,
    EventSource,
)

if TYPE_CHECKING:
    import threading


class FakeEventSource(EventSource):
    """Replay scripted poll results, then keep returning None."""

    def __init__(self, script: list[EventRecord | Exception | None]) -> None:
        """Hold the script of records, errors and empty polls to replay."""
        self._script = list(script)
        self.committed: list[EventRecord] = []
        self.closed = False
        self.stop_when_exhausted: threading.Event | None = None

    def poll(self, timeout: float) -> EventRecord | None:
        """Replay the next scripted item: a record, an empty poll or an error raised to the caller."""
        if not self._script:
            if self.stop_when_exhausted is not None:
                self.stop_when_exhausted.set()
            return None
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def commit(self, record: EventRecord) -> None:
        """Record the committed record."""
        self.committed.append(record)

    def close(self) -> None:
        """Mark the source as closed."""
        self.closed = True
