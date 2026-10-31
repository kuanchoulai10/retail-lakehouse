"""Define the SizeSource enumeration."""

from __future__ import annotations

from enum import StrEnum


class SizeSource(StrEnum):
    """Enumerate where a byte-size threshold of an operation was taken from."""

    SETTINGS = "settings"
    TABLE_PROPERTY = "table_property"
    DEFAULT = "default"
