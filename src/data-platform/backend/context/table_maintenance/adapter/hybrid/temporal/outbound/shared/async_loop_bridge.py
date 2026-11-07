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
        self._thread = threading.Thread(target=self._loop.run_forever, name="async-loop-bridge", daemon=True)
        self._lock = threading.Lock()
        self._closed = False
        self._thread.start()

    def _on_loop_thread(self) -> bool:
        return threading.get_ident() == self._thread.ident

    def run(self, coro_factory: Callable[[], Awaitable[T]], timeout: float = 30) -> T:
        """Run the coroutine built by the factory on the bridge loop; return its result.

        A timed-out run cancels the coroutine. Calling it from the loop thread
        would deadlock, so it raises RuntimeError instead.
        """
        if self._on_loop_thread():
            msg = "AsyncLoopBridge.run called from its own loop thread"
            raise RuntimeError(msg)
        with self._lock:
            if self._closed:
                msg = "AsyncLoopBridge is closed"
                raise RuntimeError(msg)

            async def call() -> T:
                return await coro_factory()

            future = asyncio.run_coroutine_threadsafe(call(), self._loop)
        try:
            return future.result(timeout)
        except TimeoutError:
            future.cancel()
            raise

    def close(self) -> None:
        """Cancel pending tasks, shut down async generators, stop the loop and join."""
        if self._on_loop_thread():
            msg = "AsyncLoopBridge.close called from its own loop thread"
            raise RuntimeError(msg)
        with self._lock:
            if self._closed:
                return
            self._closed = True
            asyncio.run_coroutine_threadsafe(self._drain(), self._loop).result(30)
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join()
            self._loop.close()

    async def _drain(self) -> None:
        current = asyncio.current_task()
        pending = [t for t in asyncio.all_tasks() if t is not current]
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        await asyncio.get_running_loop().shutdown_asyncgens()
