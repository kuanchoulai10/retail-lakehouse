"""Test the event consumer process: signal handling and shutdown of its source and bridge."""

from __future__ import annotations

import os
import signal
import threading
from typing import TYPE_CHECKING, Any, cast

import pytest

from bootstrap.container import build_repositories, build_use_cases
from bootstrap.event_consumer import run_event_consumer_process
from context.table_maintenance.adapter.inbound.event_consumer import (
    EventRecord,
    EventSource,
)
from tests.bootstrap.container.container_support import (
    NOW,
    fake_gateways,
    sqlite_engine,
    sqlite_settings,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import AsyncLoopBridge


@pytest.fixture(autouse=True)
def _restore_signal_handlers() -> Iterator[None]:
    saved = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGINT)}
    yield
    for signum, handler in saved.items():
        signal.signal(signum, handler)


class FakeBridge:
    """Async loop bridge stub that records when it is closed."""

    def __init__(self) -> None:
        """Start with the bridge open."""
        self.closed = False

    def close(self) -> None:
        """Mark the bridge as closed."""
        self.closed = True


class OnFirstPollSource(EventSource):
    """Event source that runs a callback on its first poll and fails if polled again."""

    def __init__(self, on_first_poll: Callable[[], None]) -> None:
        """Hold the callback to run on the first poll."""
        self.on_first_poll = on_first_poll
        self.polls = 0
        self.closed = False

    def poll(self, timeout: float) -> EventRecord | None:
        """Run the callback on the first poll and return no record."""
        self.polls += 1
        if self.polls == 1:
            self.on_first_poll()
        if self.polls > 50:
            raise AssertionError("consumer did not stop")
        return None

    def commit(self, record: EventRecord) -> None:
        """Accept a commit without doing anything."""
        pass

    def close(self) -> None:
        """Mark the source as closed."""
        self.closed = True


def _use_cases(settings: Any, bridge: Any) -> Any:  # noqa: ANN401
    return build_use_cases(build_repositories(sqlite_engine()), fake_gateways(), clock=lambda: NOW)


def test_sigterm_sets_the_stop_event_and_closes_source_and_bridge():
    """SIGTERM sets the stop event and the source and bridge are closed."""
    stop_event = threading.Event()
    bridge = FakeBridge()
    source = OnFirstPollSource(lambda: os.kill(os.getpid(), signal.SIGTERM))
    sources: list[tuple[str, str]] = []

    def source_factory(servers: str, topic: str) -> EventSource:
        sources.append((servers, topic))
        return source

    settings = sqlite_settings()
    run_event_consumer_process(
        settings,
        stop_event=stop_event,
        bridge_factory=lambda: cast("AsyncLoopBridge", bridge),
        use_cases_builder=_use_cases,
        source_factory=source_factory,
    )

    assert stop_event.is_set()
    assert source.closed is True
    assert bridge.closed is True
    assert sources == [(settings.kafka.bootstrap_servers, settings.kafka.topic)]


def test_injected_stop_closes_the_bridge():
    """An injected stop event ends the consumer and closes the bridge."""
    stop_event = threading.Event()
    bridge = FakeBridge()
    callbacks: list[Callable[[], None]] = []

    def _fire_first_callback() -> None:
        callbacks[0]()

    source = OnFirstPollSource(_fire_first_callback)

    run_event_consumer_process(
        sqlite_settings(),
        stop_event=stop_event,
        bridge_factory=lambda: cast("AsyncLoopBridge", bridge),
        use_cases_builder=_use_cases,
        source_factory=lambda *_: source,
        install_stop=callbacks.append,
    )

    assert stop_event.is_set()
    assert bridge.closed is True
