"""Tests for EventHandler ABC."""

from __future__ import annotations

import pytest

from base import DomainEvent, EventHandler


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
