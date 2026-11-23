"""Define the TablePropertyReset value object."""

from __future__ import annotations

from base import ReadOnlyMapping, ValueObject


class TablePropertyReset(ValueObject):
    """The change that resets properties to default: keys to write with their default, keys to remove."""

    updates: ReadOnlyMapping[str, str]
    removals: tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        """Return True when nothing needs to change."""
        return not self.updates and not self.removals
