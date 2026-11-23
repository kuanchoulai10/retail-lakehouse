"""Define the TableReconciliationActivity names."""

from __future__ import annotations

from enum import StrEnum


class TableReconciliationActivity(StrEnum):
    """Name the activities a table reconciliation workflow calls."""

    PLAN_TABLE_MAINTENANCE = "plan_table_maintenance"
    RECORD_TABLE_RECONCILIATION = "record_table_reconciliation"
    GET_WORKFLOW_RUNNING = "get_workflow_running"
    CREATE_MAINTENANCE_RUNS = "create_maintenance_runs"
    SKIP_MAINTENANCE_RUNS = "skip_maintenance_runs"
    ISSUE_RECONCILIATION_ID = "issue_reconciliation_id"
    ISSUE_RUN_IDS = "issue_run_ids"
