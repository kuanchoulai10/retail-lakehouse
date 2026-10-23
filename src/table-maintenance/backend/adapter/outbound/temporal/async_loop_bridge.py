"""Define the AsyncLoopBridge sync-to-async helper."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class AsyncLoopBridge:
    """Run coroutines on a private event loop owned by a daemon thread."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever, name="async-loop-bridge", daemon=True
        )
        self._thread.start()

    def run(self, coro_factory: Callable[[], Awaitable[T]], timeout: float = 30) -> T:
        """Run the coroutine built by the factory on the bridge loop; return its result."""

        async def call() -> T:
            return await coro_factory()

        future = asyncio.run_coroutine_threadsafe(call(), self._loop)
        return future.result(timeout)

    def close(self) -> None:
        """Stop the loop and join the thread."""
        if self._loop.is_closed():
            return
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join()
        self._loop.close()
