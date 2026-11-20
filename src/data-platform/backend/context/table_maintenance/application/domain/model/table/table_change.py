"""Define the TableChange enum."""

from __future__ import annotations

from enum import StrEnum


class TableChange(StrEnum):
    """What changed about a table, as told to the maintenance runtime."""

    UPDATED = "updated"
    POLICY_CHANGED = "policy_changed"
    STOPPED = "stopped"
    MAINTENANCE_REQUESTED = "maintenance_requested"
    RECONCILE_REQUESTED = "reconcile_requested"
    SEEN = "seen"
    MANAGED = "managed"
