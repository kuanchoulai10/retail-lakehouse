"""Provide interrupt_on_sigterm, which lets a pod's SIGTERM unwind pytest so the cleanup runs."""

from __future__ import annotations

import signal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import FrameType


def interrupt_on_sigterm() -> None:
    """Turn the first SIGTERM into ``KeyboardInterrupt`` and ignore the ones after it.

    pytest runs as the container's PID 1, which ignores a SIGTERM it has no handler for, so a pod
    ended by its deadline, an eviction or a delete would be killed after its grace period without
    tearing down a fixture. An interrupt makes pytest tear the session down, cleanup included.
    """

    def interrupt(_signal: int, _frame: FrameType | None) -> None:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
