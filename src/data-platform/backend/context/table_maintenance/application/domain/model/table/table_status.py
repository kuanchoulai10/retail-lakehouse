"""Define the TableStatus enumeration."""

from __future__ import annotations

from enum import StrEnum


class TableStatus(StrEnum):
    """Enumerate the lifecycle states of a table.

    A managed table is one its nearest discovery policy manages; an unmanaged one is
    kept with its history, whether no policy ever managed it or its policy stopped.
    """

    MANAGED = "managed"
    UNMANAGED = "unmanaged"
    DROPPED = "dropped"
