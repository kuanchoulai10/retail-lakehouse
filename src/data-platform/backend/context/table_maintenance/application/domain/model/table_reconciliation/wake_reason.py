"""Define the WakeReason enumeration."""

from __future__ import annotations

from enum import StrEnum


class WakeReason(StrEnum):
    """Enumerate why a table's reconciliation was woken."""

    SCHEDULE = "schedule"
    CATALOG_COMMIT = "catalog_commit"
    SETTINGS_CHANGED = "settings_changed"
    RESUMED = "resumed"
    PAUSED = "paused"
    MANUAL_RUN = "manual_run"
    RECONCILE_NOW = "reconcile_now"
    PREVIOUS_RUN_FINISHED = "previous_run_finished"
