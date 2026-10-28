"""Workflow identifiers, signal names and the task queue shared across components.

Workflow and schedule IDs are ``key=value`` segments joined by ``:`` after a
leading name segment, e.g. ``table-reconciliation:table-uuid=<uuid>``.
"""

from __future__ import annotations

TASK_QUEUE = "table-maintenance"

TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID = "table-maintenance-admission"
TABLE_DISCOVERY_SCHEDULE_ID_PREFIX = "table-discovery:catalog="

SIGNAL_SETTINGS_CHANGED = "settings_changed"
SIGNAL_TABLE_UPDATED = "table_updated"
SIGNAL_TRIGGER_NOW = "trigger_now"
SIGNAL_PAUSE = "pause"
SIGNAL_RESUME = "resume"
SIGNAL_STOP = "stop"
SIGNAL_MAINTENANCE_FINISHED = "maintenance_finished"
SIGNAL_OPERATION_RESULT = "operation_result"
SIGNAL_ADMISSION_ACQUIRE = "acquire"
SIGNAL_ADMISSION_RELEASE = "release"
SIGNAL_ADMISSION_GRANTED = "admission_granted"


def table_reconciliation_workflow_id(table_uuid: str) -> str:
    """Return the workflow ID of the reconciliation workflow for a table."""
    return f"table-reconciliation:table-uuid={table_uuid}"


def table_maintenance_workflow_id(table: str, run_id: str) -> str:
    """Return the workflow ID of the table maintenance workflow for a run.

    ``table`` is the fully qualified ``catalog.namespace.table`` name as of the
    run start; a later rename does not change the ID, so paths that only know
    the run look the ID up on the maintenance run instead of rebuilding it.
    """
    return f"table-maintenance:table={table}:run={run_id}"


def table_discovery_adhoc_workflow_id(catalog: str, namespace: str | None) -> str:
    """Return the workflow ID of an ad-hoc discovery run for a catalog or namespace.

    The ``trigger=adhoc`` segment keeps it distinct from the scheduled runs.
    """
    scope = (
        f"catalog={catalog}"
        if namespace is None
        else (f"catalog={catalog}:namespace={namespace}")
    )
    return f"table-discovery:{scope}:trigger=adhoc"


def table_discovery_schedule_id(catalog: str) -> str:
    """Return the ID of the discovery schedule of a catalog (one schedule per catalog)."""
    return f"{TABLE_DISCOVERY_SCHEDULE_ID_PREFIX}{catalog}"
