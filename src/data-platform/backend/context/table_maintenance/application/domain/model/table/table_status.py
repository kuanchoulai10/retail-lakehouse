"""Define the TableStatus enumeration."""

from __future__ import annotations

from enum import StrEnum


class TableStatus(StrEnum):
    """Enumerate the lifecycle states of a table.

    A managed table is one its nearest discovery policy manages; an unmanaged one is
    kept with its history, whether no policy ever managed it or its policy stopped. An
    undecided table was given a policy of its own before discovery saw it: it is not
    managed, and only a discovery decision moves it to managed or unmanaged.
    """

    MANAGED = "managed"
    UNMANAGED = "unmanaged"
    UNDECIDED = "undecided"
    DROPPED = "dropped"
