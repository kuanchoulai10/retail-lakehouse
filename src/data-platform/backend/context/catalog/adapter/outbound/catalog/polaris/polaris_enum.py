"""Define the polaris_enum function."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from enum import StrEnum


def polaris_enum[E: StrEnum](enum: type[E], value: object, what: str) -> E:
    """Return the member of ``enum`` that Polaris sent, or raise ValueError naming the unknown ``what``."""
    try:
        return enum(value)
    except ValueError:
        raise ValueError(f"unknown {what} {value!r}") from None
