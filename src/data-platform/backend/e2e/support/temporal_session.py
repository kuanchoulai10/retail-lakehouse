"""Provide TemporalSession, which lets the synchronous scenarios use the asynchronous Temporal client."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class TemporalSession[C]:
    """Hold one connected client on one event loop, and run coroutines with it."""

    def __init__(self, loop: asyncio.AbstractEventLoop, client: C) -> None:
        """Keep ``client``, which was connected on ``loop``."""
        self._loop = loop
        self._client = client

    @classmethod
    def connect(cls, connect: Callable[[], Awaitable[C]]) -> TemporalSession[C]:
        """Connect on a new event loop that the session keeps."""
        loop = asyncio.new_event_loop()
        return cls(loop, loop.run_until_complete(connect()))

    def run[R](self, call: Callable[[C], Awaitable[R]]) -> R:
        """Run ``call`` with the client and return its result."""
        return self._loop.run_until_complete(call(self._client))

    def close(self) -> None:
        """Close the event loop."""
        self._loop.close()
