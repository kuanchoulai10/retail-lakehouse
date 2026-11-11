"""Define the RemoveOrphanFilesConditions value object."""

from __future__ import annotations

from base import ValueObject


class RemoveOrphanFilesConditions(ValueObject):
    """Conditions that make orphan file removal worth running; there are none yet."""

    def is_empty(self) -> bool:
        """Return whether no condition is set."""
        return True
