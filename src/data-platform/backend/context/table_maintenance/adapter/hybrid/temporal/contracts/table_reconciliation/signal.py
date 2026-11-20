"""Define the TableReconciliationSignal names."""

from __future__ import annotations

from enum import StrEnum


class TableReconciliationSignal(StrEnum):
    """Name the signals a table reconciliation workflow receives."""

    POLICY_CHANGED = "policy_changed"
    TABLE_UPDATED = "table_updated"
    TRIGGER_NOW = "trigger_now"
    STOP = "stop"
    MAINTENANCE_FINISHED = "maintenance_finished"
    RECONCILE_NOW = "reconcile_now"
    TABLE_SEEN = "table_seen"
    TABLE_MANAGED = "table_managed"
