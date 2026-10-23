"""Workflow identifiers, signal names and the task queue shared across components."""

from __future__ import annotations

TASK_QUEUE = "table-maintenance"

CAPACITY_WORKFLOW_ID = "maintenance-capacity"
DISCOVERY_SCHEDULE_ID = "table-discovery"

SIGNAL_SETTINGS_CHANGED = "settings_changed"
SIGNAL_TABLE_UPDATED = "table_updated"
SIGNAL_TRIGGER_NOW = "trigger_now"
SIGNAL_PAUSE = "pause"
SIGNAL_RESUME = "resume"
SIGNAL_STOP = "stop"
SIGNAL_MAINTENANCE_FINISHED = "maintenance_finished"
SIGNAL_OPERATION_RESULT = "operation_result"
SIGNAL_CAPACITY_ACQUIRE = "acquire"
SIGNAL_CAPACITY_RELEASE = "release"
SIGNAL_CAPACITY_GRANTED = "capacity_granted"


def table_reconcile_workflow_id(table_uuid: str) -> str:
    """Return the workflow ID of the reconcile workflow for a table."""
    return f"table-reconcile-{table_uuid}"


def maintenance_workflow_id(run_id: str) -> str:
    """Return the workflow ID of the maintenance workflow for a run."""
    return f"maintenance-{run_id}"


def discovery_adhoc_workflow_id(catalog: str, namespace: str | None) -> str:
    """Return the workflow ID of an ad-hoc discovery run for a catalog or namespace."""
    return f"table-discovery-adhoc-{catalog}-{namespace or 'all'}"
