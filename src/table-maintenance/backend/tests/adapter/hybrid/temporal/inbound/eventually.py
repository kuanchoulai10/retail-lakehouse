"""Define the eventually polling helper for asynchronous assertions."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


async def eventually(
    probe: Callable[[], Awaitable[Any]],
    predicate: Callable[[Any], bool],
    timeout: float = 10.0,
) -> Any:  # noqa: ANN401
    """Poll ``probe`` until ``predicate`` holds on its value; fail after ``timeout``."""
    deadline = time.monotonic() + timeout
    value = await probe()
    while not predicate(value):
        if time.monotonic() > deadline:
            raise AssertionError(f"condition never held; last value {value!r}")
        await asyncio.sleep(0.05)
        value = await probe()
    return value
