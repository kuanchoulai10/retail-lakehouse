"""Define the TableReconciliationSignal names."""

from __future__ import annotations

from enum import StrEnum


class TableReconciliationSignal(StrEnum):
    """Name the signals a table reconciliation workflow receives."""

    SETTINGS_CHANGED = "settings_changed"
    TABLE_UPDATED = "table_updated"
    TRIGGER_NOW = "trigger_now"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    MAINTENANCE_FINISHED = "maintenance_finished"
