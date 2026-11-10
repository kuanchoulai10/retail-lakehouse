"""Define validation_message."""

from __future__ import annotations

from pydantic import ValidationError

_VALUE_ERROR_PREFIX = "Value error, "


def validation_message(exc: ValueError) -> str:
    """Return a one-line message for ``exc``.

    For a Pydantic ``ValidationError``, the first error as
    ``"<dotted.loc>: <msg>"`` (just ``<msg>`` for a model-level error),
    without Pydantic's ``"Value error, "`` prefix; otherwise ``str(exc)``.
    """
    if not isinstance(exc, ValidationError):
        return str(exc)
    first = exc.errors()[0]
    message = first["msg"].removeprefix(_VALUE_ERROR_PREFIX)
    loc = ".".join(str(part) for part in first["loc"])
    return f"{loc}: {message}" if loc else message
