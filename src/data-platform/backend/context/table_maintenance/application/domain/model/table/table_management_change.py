"""Define the TableManagementChange enumeration."""

from __future__ import annotations

from enum import StrEnum


class TableManagementChange(StrEnum):
    """Enumerate what a discovery decision changed about a known table.

    ``MANAGED`` and ``UNMANAGED`` mean the table changed management.
    ``RULE_CHANGED`` means a managed table stays managed but another include
    rule now decides it, so only its matched rule changed. ``UNCHANGED`` means
    nothing changed.
    """

    UNCHANGED = "unchanged"
    MANAGED = "managed"
    UNMANAGED = "unmanaged"
    RULE_CHANGED = "rule_changed"
