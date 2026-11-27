"""Define the TableDiscoveryRoundActivity names."""

from __future__ import annotations

from enum import StrEnum


class TableDiscoveryRoundActivity(StrEnum):
    """Name the activities a table discovery round calls."""

    LIST_SCANNED_CATALOGS = "list_scanned_catalogs"
