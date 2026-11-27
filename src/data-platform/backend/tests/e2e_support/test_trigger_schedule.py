"""Test trigger_schedule, which has Temporal run a schedule's action now."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import cast

from temporalio.client import Client, ScheduleOverlapPolicy

from e2e.support import TemporalSession, trigger_schedule


class _Client:
    def __init__(self) -> None:
        self.triggered: list[tuple[str, ScheduleOverlapPolicy | None]] = []

    def get_schedule_handle(self, schedule_id: str) -> SimpleNamespace:
        async def trigger(*, overlap: ScheduleOverlapPolicy | None = None) -> None:
            self.triggered.append((schedule_id, overlap))

        return SimpleNamespace(trigger=trigger)


def test_the_schedule_is_triggered_once_and_never_skipped_behind_a_running_action():
    """BUFFER_ONE: a round still going when the trigger lands runs this one after it, instead of dropping it."""
    client = _Client()
    session = TemporalSession(asyncio.new_event_loop(), cast(Client, client))
    try:
        trigger_schedule(session, "table-discovery")
    finally:
        session.close()
    assert client.triggered == [("table-discovery", ScheduleOverlapPolicy.BUFFER_ONE)]
