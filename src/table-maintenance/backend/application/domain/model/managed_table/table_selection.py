"""Define the TableSelection enumeration."""

from __future__ import annotations

from enum import StrEnum


class TableSelection(StrEnum):
    """Enumerate how a table came to be managed."""

    AUTO = "auto"
    MANUAL = "manual"
