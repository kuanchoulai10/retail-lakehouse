"""Provide BackgroundWriter, a thread that keeps appending to a table while a scenario watches the platform."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class BackgroundWriter:
    """Call ``append(index)`` every ``every_seconds`` until stopped, numbering the appends from zero.

    The first append that raises ends the thread, and ``stop`` raises it: a commit conflict fails
    the scenario instead of vanishing. Push ``stop`` on the cleanup stack right after ``start`` so
    the writes end on every path.
    """

    def __init__(self, append: Callable[[int], None], every_seconds: float) -> None:
        """Write with ``append`` every ``every_seconds``."""
        self._append = append
        self._every_seconds = every_seconds
        self._stopped = threading.Event()
        self._error: BaseException | None = None
        self._count = 0
        self._thread = threading.Thread(target=self._run, name="background-writer", daemon=True)

    @classmethod
    def start(cls, append: Callable[[int], None], *, every_seconds: float) -> BackgroundWriter:
        """Start writing; the first append comes ``every_seconds`` from now."""
        writer = cls(append, every_seconds)
        writer._thread.start()
        return writer

    @property
    def running(self) -> bool:
        """Say whether the thread still writes."""
        return self._thread.is_alive()

    def stop(self) -> int:
        """Stop writing, wait for the thread and return how many appends committed; raise the append error."""
        self._stopped.set()
        self._thread.join(timeout=self._every_seconds + 120)
        assert not self._thread.is_alive(), "the background writer did not stop"
        if self._error is not None:
            raise self._error
        return self._count

    def _run(self) -> None:
        while not self._stopped.wait(self._every_seconds):
            try:
                self._append(self._count)
            except BaseException as error:  # noqa: BLE001
                self._error = error
                return
            self._count += 1
