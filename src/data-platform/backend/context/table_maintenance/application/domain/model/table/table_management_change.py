"""Define the TableManagementChange enumeration."""

from __future__ import annotations

from enum import StrEnum


class TableManagementChange(StrEnum):
    """Enumerate what a discovery decision changed about whether a known table is managed."""

    UNCHANGED = "unchanged"
    MANAGED = "managed"
    UNMANAGED = "unmanaged"
