"""Define the TableManagementChange enumeration."""

from __future__ import annotations

from enum import StrEnum


class TableManagementChange(StrEnum):
    """Enumerate what a management decision changed about a known table.

    ``MANAGED`` and ``UNMANAGED`` mean the table changed management.
    ``DECISION_CHANGED`` means its management stays the same, managed or not, but
    another policy, version or rule decides it now (or no policy any more), so only
    what decided it changed: it is saved and nothing is sent. ``UNCHANGED`` means
    nothing changed.
    """

    UNCHANGED = "unchanged"
    MANAGED = "managed"
    UNMANAGED = "unmanaged"
    DECISION_CHANGED = "decision_changed"
