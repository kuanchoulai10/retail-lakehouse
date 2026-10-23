"""Test AsyncLoopBridge."""

from __future__ import annotations

import asyncio
import threading

import pytest

from adapter.outbound.temporal.async_loop_bridge import AsyncLoopBridge


def test_run_returns_result_from_a_separate_thread():
    bridge = AsyncLoopBridge()
    try:

        async def work() -> tuple[int, int]:
            await asyncio.sleep(0)
            return 42, threading.get_ident()

        value, thread_id = bridge.run(work)
        assert value == 42
        assert thread_id != threading.get_ident()
    finally:
        bridge.close()


def test_run_propagates_exceptions():
    bridge = AsyncLoopBridge()
    try:

        async def boom() -> None:
            msg = "boom"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="boom"):
            bridge.run(boom)
    finally:
        bridge.close()


def test_close_is_idempotent():
    bridge = AsyncLoopBridge()
    bridge.close()
    bridge.close()
