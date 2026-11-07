"""Test the event consumer loop runner."""

from __future__ import annotations

import threading

from bootstrap.container import build_repositories, build_use_cases, run_event_consumer
from context.table_maintenance.adapter.inbound.event_consumer import (
    EventRecord,
    EventSource,
)
from tests.bootstrap.container.container_support import (
    NOW,
    fake_gateways,
    sqlite_engine,
)


class ScriptedSource(EventSource):
    """Event source that returns scripted records, then stops the loop."""

    def __init__(self, records: list[EventRecord], stop: threading.Event) -> None:
        """Hold the scripted records and the stop event to set when they run out."""
        self.records = list(records)
        self.stop = stop
        self.committed: list[int] = []
        self.closed = False

    def poll(self, timeout: float) -> EventRecord | None:
        """Return the next scripted record, or None and stop the loop when none are left."""
        if not self.records:
            self.stop.set()
            return None
        return self.records.pop(0)

    def commit(self, record: EventRecord) -> None:
        """Record the offset of a committed record."""
        self.committed.append(record.offset)

    def close(self) -> None:
        """Mark the source as closed."""
        self.closed = True


def test_consumer_runs_until_stopped_and_closes_the_source():
    """The consumer commits each record, runs until stopped and closes the source."""
    stop = threading.Event()
    source = ScriptedSource(
        [
            EventRecord(value=b"not json", topic="t", partition=0, offset=7),
            EventRecord(value=None, topic="t", partition=0, offset=8),
        ],
        stop,
    )
    use_cases = build_use_cases(build_repositories(sqlite_engine()), fake_gateways(), clock=lambda: NOW)

    run_event_consumer(use_cases, source, stop)

    assert source.committed == [7, 8]
    assert source.closed is True
