"""Define the TableStatus enumeration."""

from __future__ import annotations

from enum import StrEnum


class TableStatus(StrEnum):
    """Enumerate the lifecycle states of a table."""

    ACTIVE = "active"
    PAUSED = "paused"
    EXCLUDED = "excluded"
    DROPPED = "dropped"
