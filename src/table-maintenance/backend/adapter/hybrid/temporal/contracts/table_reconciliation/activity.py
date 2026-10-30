"""Define the TableReconciliationActivity names."""

from __future__ import annotations

from enum import StrEnum


class TableReconciliationActivity(StrEnum):
    """Name the activities a table reconciliation workflow calls."""

    PLAN_TABLE_MAINTENANCE = "plan_table_maintenance"
