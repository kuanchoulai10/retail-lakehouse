"""Define the TableDiscoveryActivity names."""

from __future__ import annotations

from enum import StrEnum


class TableDiscoveryActivity(StrEnum):
    """Name the activities a table discovery workflow calls."""

    SYNC_DISCOVERED_TABLES = "sync_discovered_tables"
