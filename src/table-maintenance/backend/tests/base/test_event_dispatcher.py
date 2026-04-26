"""Tests for EventDispatcher."""

from dataclasses import dataclass

from base import DomainEvent
from base.event_dispatcher import EventDispatcher
from base.event_handler import EventHandler


@dataclass(frozen=True)
class _EventA(DomainEvent):
    value: str


@dataclass(frozen=True)
class _EventB(DomainEvent):
    value: int


class _RecordingHandler(EventHandler):
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    def handle(self, event: DomainEvent) -> None:
        self.events.append(event)


class TestDispatch:
    """Tests for EventDispatcher.dispatch()."""

    def test_dispatch_to_registered_handler(self):
        """Verify event is dispatched to the correct handler."""
        dispatcher = EventDispatcher()
        handler = _RecordingHandler()
        dispatcher.register(_EventA, handler)
        ev = _EventA(value="hello")
        dispatcher.dispatch(ev)
        assert handler.events == [ev]

    def test_dispatch_ignores_unregistered_event(self):
        """Verify unregistered event types are silently ignored."""
        dispatcher = EventDispatcher()
        handler = _RecordingHandler()
        dispatcher.register(_EventA, handler)
        dispatcher.dispatch(_EventB(value=42))
        assert handler.events == []

    def test_dispatch_to_multiple_handlers(self):
        """Verify event is dispatched to all registered handlers for that type."""
        dispatcher = EventDispatcher()
        h1 = _RecordingHandler()
        h2 = _RecordingHandler()
        dispatcher.register(_EventA, h1)
        dispatcher.register(_EventA, h2)
        ev = _EventA(value="hello")
        dispatcher.dispatch(ev)
        assert h1.events == [ev]
        assert h2.events == [ev]


class TestDispatchAll:
    """Tests for EventDispatcher.dispatch_all()."""

    def test_dispatch_all_routes_each_event(self):
        """Verify dispatch_all routes each event to its handler."""
        dispatcher = EventDispatcher()
        ha = _RecordingHandler()
        hb = _RecordingHandler()
        dispatcher.register(_EventA, ha)
        dispatcher.register(_EventB, hb)
        ea = _EventA(value="a")
        eb = _EventB(value=1)
        dispatcher.dispatch_all([ea, eb])
        assert ha.events == [ea]
        assert hb.events == [eb]

    def test_dispatch_all_empty_list(self):
        """Verify dispatch_all with empty list does nothing."""
        dispatcher = EventDispatcher()
        dispatcher.dispatch_all([])
