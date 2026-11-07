"""Define the TableChange enum."""

from __future__ import annotations

from enum import StrEnum


class TableChange(StrEnum):
    """What changed about a table, as told to the maintenance runtime."""

    UPDATED = "updated"
    SETTINGS_CHANGED = "settings_changed"
    PAUSED = "paused"
    RESUMED = "resumed"
    STOPPED = "stopped"
    MAINTENANCE_REQUESTED = "maintenance_requested"
