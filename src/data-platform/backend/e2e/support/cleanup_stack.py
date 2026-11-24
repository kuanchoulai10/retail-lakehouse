"""Provide CleanupStack, which undoes what a scenario created even when the scenario fails."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class CleanupStack:
    """Hold the undo actions of a scenario and run them newest first."""

    def __init__(self) -> None:
        """Start with nothing to undo."""
        self._actions: list[tuple[str, Callable[[], object]]] = []

    def push(self, what: str, action: Callable[[], object]) -> None:
        """Remember to run ``action`` to undo ``what``."""
        self._actions.append((what, action))

    def run(self) -> list[str]:
        """Run every action, newest first, and return one ``"<what>: <error>"`` line per failure.

        An interrupt (the pod's SIGTERM) in one action does not stop the others; once they ran it is
        raised again with every failure, so the session still ends.
        """
        errors: list[str] = []
        interrupted = False
        while self._actions:
            what, action = self._actions.pop()
            try:
                action()
            except KeyboardInterrupt:
                interrupted = True
                errors.append(f"{what}: interrupted")
            except Exception as error:  # noqa: BLE001 - every undo runs, failures are reported together
                errors.append(f"{what}: {error!r}")
        if interrupted:
            raise KeyboardInterrupt("; ".join(errors))
        return errors
