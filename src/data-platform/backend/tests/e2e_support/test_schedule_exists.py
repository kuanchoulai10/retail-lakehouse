"""Test schedule_exists, which asks Temporal whether a schedule is there."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import cast

import pytest
from temporalio.client import Client
from temporalio.service import RPCError, RPCStatusCode

from e2e.support import TemporalSession, schedule_exists


class _Client:
    def __init__(self, error: RPCError | None) -> None:
        self.asked: list[str] = []
        self._error = error

    def get_schedule_handle(self, schedule_id: str) -> SimpleNamespace:
        async def describe() -> SimpleNamespace:
            self.asked.append(schedule_id)
            if self._error:
                raise self._error
            return SimpleNamespace(id=schedule_id)

        return SimpleNamespace(describe=describe)


def _exists(error: RPCError | None) -> tuple[bool, list[str]]:
    client = _Client(error)
    session = TemporalSession(asyncio.new_event_loop(), cast(Client, client))
    try:
        return schedule_exists(session, "table-discovery:catalog=c"), client.asked
    finally:
        session.close()


def test_a_schedule_temporal_describes_exists():
    """The schedule asked for is described."""
    assert _exists(None) == (True, ["table-discovery:catalog=c"])


def test_a_schedule_temporal_does_not_know_does_not_exist():
    """NOT_FOUND is the answer "no", not an error."""
    assert _exists(RPCError("gone", RPCStatusCode.NOT_FOUND, b""))[0] is False


def test_any_other_failure_is_raised():
    """A Temporal that does not answer is never read as "the schedule is gone"."""
    with pytest.raises(RPCError):
        _exists(RPCError("down", RPCStatusCode.UNAVAILABLE, b""))
