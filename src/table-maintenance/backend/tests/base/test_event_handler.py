"""Tests for EventHandler ABC."""

from dataclasses import dataclass

import pytest

from core.base import DomainEvent
from core.base.event_handler import EventHandler


@dataclass(frozen=True)
class _StubEvent(DomainEvent):
    value: str


def test_is_abstract():
    """Verify EventHandler cannot be instantiated directly."""
    with pytest.raises(TypeError):
        EventHandler()


def test_concrete_handler_can_handle():
    """Verify a concrete EventHandler subclass can handle events."""
    handled: list[_StubEvent] = []

    class _StubHandler(EventHandler[_StubEvent]):
        def handle(self, event: _StubEvent) -> None:
            handled.append(event)

    handler = _StubHandler()
    ev = _StubEvent(value="hello")
    handler.handle(ev)
    assert handled == [ev]
