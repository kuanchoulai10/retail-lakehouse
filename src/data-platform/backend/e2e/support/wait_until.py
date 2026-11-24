"""Provide wait_until, the bounded poll every e2e wait uses."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def wait_until[T](
    probe: Callable[[], T | None],
    *,
    timeout: float,
    interval: float,
    what: str,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call ``probe`` until it returns something other than None, and return that.

    An exception from ``probe`` counts as "not yet". After ``timeout`` seconds the wait fails,
    naming ``what`` it waited for and the last value or error it saw.
    """
    deadline = clock() + timeout
    last: object = None
    while True:
        try:
            value = probe()
        except Exception as error:  # noqa: BLE001 - any failure of the probe means "not yet"
            last = error
        else:
            if value is not None:
                return value
            last = value
        if clock() >= deadline:
            raise TimeoutError(f"{what} not seen within {timeout:.0f}s; last: {last!r}")
        sleep(interval)
