"""Define the TableStatus enumeration."""

from __future__ import annotations

from enum import StrEnum


class TableStatus(StrEnum):
    """Enumerate the lifecycle states of a table.

    A managed table is one the discovery rules include; an unmanaged one is kept
    with its history after the rules stopped including it.
    """

    MANAGED = "managed"
    UNMANAGED = "unmanaged"
    DROPPED = "dropped"
