"""Define the InvariantViolation exception."""

from __future__ import annotations

from typing import Self

from pydantic import ValidationError

_VALUE_ERROR_PREFIX = "Value error, "


class InvariantViolation(ValueError):
    """A domain object refused the data it was built or changed with.

    The model bases raise it, chained from Pydantic's error, wherever they
    validate, so Pydantic's ``ValidationError`` never leaves them. It is a
    ``ValueError``, and its string is one line naming the first problem.
    """

    def __init__(self, message: str) -> None:
        """Hold the one-line ``message``."""
        super().__init__(message)

    @classmethod
    def from_error(cls, exc: ValueError) -> Self:
        """Build the violation for ``exc``.

        For a Pydantic ``ValidationError``, the first error as
        ``"<dotted.loc>: <msg>"`` (just ``<msg>`` for a model-level error),
        without Pydantic's ``"Value error, "`` prefix; otherwise ``str(exc)``.
        """
        if not isinstance(exc, ValidationError) or not exc.errors():
            return cls(str(exc))
        first = exc.errors()[0]
        message = first["msg"].removeprefix(_VALUE_ERROR_PREFIX)
        loc = ".".join(str(part) for part in first["loc"])
        return cls(f"{loc}: {message}" if loc else message)
