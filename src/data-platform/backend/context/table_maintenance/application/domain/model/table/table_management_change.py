"""Define the TableManagementChange enumeration."""

from __future__ import annotations

from enum import StrEnum


class TableManagementChange(StrEnum):
    """Enumerate what a discovery decision changed about a known table.

    ``MANAGED`` and ``UNMANAGED`` mean the table changed management.
    ``MATCH_CHANGED`` means its management stays the same, managed or not, but
    another policy, version or rule decides it now, so only the recorded match
    changed. ``UNCHANGED`` means nothing changed.
    """

    UNCHANGED = "unchanged"
    MANAGED = "managed"
    UNMANAGED = "unmanaged"
    MATCH_CHANGED = "match_changed"
