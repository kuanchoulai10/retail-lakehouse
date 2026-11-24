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
        """Run every action, newest first, and return one ``"<what>: <error>"`` line per failure."""
        errors: list[str] = []
        while self._actions:
            what, action = self._actions.pop()
            try:
                action()
            except Exception as error:  # noqa: BLE001 - every undo runs, failures are reported together
                errors.append(f"{what}: {error!r}")
        return errors
