"""Define the GlobList value object."""

from __future__ import annotations

from fnmatch import fnmatchcase

from pydantic import field_validator

from base import ValueObject


class GlobList(ValueObject):
    """A non-empty list of case-sensitive globs; a value matches when any glob matches it."""

    globs: tuple[str, ...]

    @field_validator("globs")
    @classmethod
    def _non_empty(cls, globs: tuple[str, ...]) -> tuple[str, ...]:
        if not globs:
            raise ValueError("a discovery rule field needs at least one glob")
        if any(not glob for glob in globs):
            raise ValueError("a glob must not be empty")
        return globs

    def matches(self, value: str) -> bool:
        """Return whether any glob matches the value."""
        return any(fnmatchcase(value, glob) for glob in self.globs)
