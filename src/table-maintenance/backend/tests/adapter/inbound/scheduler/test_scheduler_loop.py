"""Tests for SchedulerLoop."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock

from adapter.inbound.scheduler.scheduler_loop import SchedulerLoop


def _make_result(count: int = 0):
    """Provide a mock ScheduleJobsUseCaseOutput."""
    result = MagicMock()
    result.triggered_count = count
    return result


def test_tick_calls_service_execute():
    """Verify that tick() calls service.execute() once."""
    service = MagicMock()
    service.execute.return_value = _make_result()
    loop = SchedulerLoop(service, interval_seconds=10)

    loop.tick()

    service.execute.assert_called_once()


def test_tick_does_not_raise_on_service_exception():
    """Verify that tick() catches and logs exceptions from service."""
    service = MagicMock()
    service.execute.side_effect = RuntimeError("boom")
    loop = SchedulerLoop(service, interval_seconds=10)

    loop.tick()  # should not raise


def test_loop_stops_on_shutdown_event():
    """Verify that start() exits when stop() is called."""
    service = MagicMock()
    service.execute.return_value = _make_result()
    loop = SchedulerLoop(service, interval_seconds=60)

    # Run in a thread and stop immediately
    t = threading.Thread(target=loop.start)
    t.start()
    loop.stop()
    t.join(timeout=2)
    assert not t.is_alive()
