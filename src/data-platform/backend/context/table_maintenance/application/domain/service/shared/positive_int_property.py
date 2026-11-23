"""Define the positive_int_property domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


def positive_int_property(properties: Mapping[str, str], key: str) -> int | None:
    """Return a table property as a positive int, or None if absent or invalid."""
    raw = properties.get(key)
    if raw is None:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None
