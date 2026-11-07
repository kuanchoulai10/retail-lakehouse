"""Test AsyncLoopBridge."""

from __future__ import annotations

import asyncio
import threading

import pytest

from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
    AsyncLoopBridge,
)


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


def test_timeout_cancels_the_coroutine():
    bridge = AsyncLoopBridge()
    outcome: dict[str, bool] = {"cancelled": False, "completed": False}
    started = threading.Event()
    cancelled = threading.Event()

    async def slow() -> None:
        started.set()
        try:
            await asyncio.sleep(30)
            outcome["completed"] = True
        except asyncio.CancelledError:
            outcome["cancelled"] = True
            cancelled.set()
            raise

    try:
        with pytest.raises(TimeoutError):
            bridge.run(slow, timeout=0.2)
        assert started.is_set()
        assert cancelled.wait(5)
        assert outcome == {"cancelled": True, "completed": False}
    finally:
        bridge.close()


def test_reentrant_run_from_loop_thread_raises():
    bridge = AsyncLoopBridge()
    try:

        async def inner() -> int:
            return 1

        async def outer() -> None:
            bridge.run(inner)

        with pytest.raises(RuntimeError, match="loop thread"):
            bridge.run(outer)
    finally:
        bridge.close()


def test_close_from_loop_thread_raises():
    bridge = AsyncLoopBridge()
    try:

        async def outer() -> None:
            bridge.close()

        with pytest.raises(RuntimeError, match="loop thread"):
            bridge.run(outer)
    finally:
        bridge.close()


def test_run_after_close_raises_without_calling_factory():
    bridge = AsyncLoopBridge()
    bridge.close()
    called = []

    def factory():
        called.append(1)
        raise AssertionError("factory must not be called")

    with pytest.raises(RuntimeError, match="closed"):
        bridge.run(factory)
    assert called == []


def test_close_cancels_pending_tasks_and_is_thread_safe():
    bridge = AsyncLoopBridge()
    cancelled = threading.Event()
    started = threading.Event()

    async def spawn() -> None:
        async def pending() -> None:
            started.set()
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                cancelled.set()
                raise

        asyncio.ensure_future(pending())

    bridge.run(spawn)
    assert started.wait(5)
    threads = [threading.Thread(target=bridge.close) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert cancelled.is_set()
