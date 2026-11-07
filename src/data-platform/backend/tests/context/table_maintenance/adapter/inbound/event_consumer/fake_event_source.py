"""Provide an in-memory EventSource that records commits."""

from __future__ import annotations

import threading

from context.table_maintenance.adapter.inbound.event_consumer import (
    EventRecord,
    EventSource,
)


class FakeEventSource(EventSource):
    """Replay scripted poll results, then keep returning None."""

    def __init__(self, script: list[EventRecord | Exception | None]) -> None:
        self._script = list(script)
        self.committed: list[EventRecord] = []
        self.closed = False
        self.stop_when_exhausted: threading.Event | None = None

    def poll(self, timeout: float) -> EventRecord | None:
        if not self._script:
            if self.stop_when_exhausted is not None:
                self.stop_when_exhausted.set()
            return None
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def commit(self, record: EventRecord) -> None:
        self.committed.append(record)

    def close(self) -> None:
        self.closed = True
