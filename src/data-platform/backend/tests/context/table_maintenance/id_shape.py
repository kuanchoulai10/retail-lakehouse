"""Provide IdShape, which tells whether a string is a valid id of one kind, by the kind's own rule."""

from __future__ import annotations

from typing import TYPE_CHECKING

from base import InvariantViolation

if TYPE_CHECKING:
    from base import EntityId


class IdShape:
    """Tell whether a string is a valid id of one kind by building that kind, so a test checks the one definition."""

    def __init__(self, kind: type[EntityId]) -> None:
        """Bind the id kind."""
        self._kind = kind

    def fullmatch(self, value: str) -> bool:
        """Return whether the kind accepts ``value``."""
        try:
            self._kind(value)
        except InvariantViolation:
            return False
        return True
