"""Define the TableNamePattern value object."""

from __future__ import annotations

from fnmatch import fnmatchcase

from pydantic import field_validator

from base import ValueObject


class TableNamePattern(ValueObject):
    """A glob on the table name alone, never on its namespace or catalog.

    It matches case-sensitively (``fnmatchcase``), at every level a policy is attached.
    """

    value: str

    @field_validator("value")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("a table name pattern must not be empty")
        return value

    def matches(self, table: str) -> bool:
        """Return whether the table name matches the pattern."""
        return fnmatchcase(table, self.value)
