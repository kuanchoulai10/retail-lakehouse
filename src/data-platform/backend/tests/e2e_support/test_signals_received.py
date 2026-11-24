"""Test signals_received, which lists the signals a workflow got, oldest first."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import cast

from temporalio.api.enums.v1 import EventType
from temporalio.client import Client

from e2e.support import TemporalSession, signals_received


def _event(event_type: int, name: str = "") -> SimpleNamespace:
    signaled = SimpleNamespace(signal_name=name)
    return SimpleNamespace(event_type=event_type, workflow_execution_signaled_event_attributes=signaled)


class _Client:
    def __init__(self, events: list[SimpleNamespace]) -> None:
        self.asked: list[str] = []
        self._events = events

    def get_workflow_handle(self, workflow_id: str) -> SimpleNamespace:
        async def fetch_history() -> SimpleNamespace:
            self.asked.append(workflow_id)
            return SimpleNamespace(events=self._events)

        return SimpleNamespace(fetch_history=fetch_history)


def test_only_signals_are_listed_by_name_in_order():
    """Other events are left out; repeated signals are each listed."""
    client = _Client(
        [
            _event(EventType.EVENT_TYPE_WORKFLOW_EXECUTION_STARTED),
            _event(EventType.EVENT_TYPE_WORKFLOW_EXECUTION_SIGNALED, "wake"),
            _event(EventType.EVENT_TYPE_TIMER_STARTED),
            _event(EventType.EVENT_TYPE_WORKFLOW_EXECUTION_SIGNALED, "stop"),
        ]
    )
    session = TemporalSession(asyncio.new_event_loop(), cast(Client, client))
    try:
        assert signals_received(session, "table-reconciliation:table-uuid=u") == ["wake", "stop"]
    finally:
        session.close()
    assert client.asked == ["table-reconciliation:table-uuid=u"]
