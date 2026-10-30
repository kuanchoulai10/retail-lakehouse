"""Pin the names Temporal stores in workflow histories and schedules.

Workflow types, signal names, activity names, the task queue and the fixed IDs
travel over the wire and are recorded in running histories, so moving or
renaming the Python symbols must never change these strings.
"""

from __future__ import annotations

from enum import StrEnum

from adapter.hybrid.temporal.contracts.shared import TASK_QUEUE
from adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_SCHEDULE_ID_PREFIX,
    TABLE_DISCOVERY_WORKFLOW,
    TableDiscoveryActivity,
)
from adapter.hybrid.temporal.contracts.table_maintenance import (
    TABLE_MAINTENANCE_WORKFLOW,
    TableMaintenanceActivity,
    TableMaintenanceSignal,
)
from adapter.hybrid.temporal.contracts.table_maintenance_admission import (
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW,
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID,
    TableMaintenanceAdmissionSignal,
)
from adapter.hybrid.temporal.contracts.table_reconciliation import (
    TABLE_RECONCILIATION_WORKFLOW,
    TableReconciliationActivity,
    TableReconciliationSignal,
)


def _values(enum: type[StrEnum]) -> dict[str, str]:
    return {member.name: member.value for member in enum}


def test_workflow_type_names():
    assert TABLE_DISCOVERY_WORKFLOW == "TableDiscoveryWorkflow"
    assert TABLE_RECONCILIATION_WORKFLOW == "TableReconciliationWorkflow"
    assert TABLE_MAINTENANCE_WORKFLOW == "TableMaintenanceWorkflow"
    assert TABLE_MAINTENANCE_ADMISSION_WORKFLOW == "TableMaintenanceAdmissionWorkflow"


def test_task_queue_and_fixed_ids():
    assert TASK_QUEUE == "table-maintenance"
    assert TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID == "table-maintenance-admission"
    assert TABLE_DISCOVERY_SCHEDULE_ID_PREFIX == "table-discovery:catalog="


def test_table_reconciliation_signals():
    assert _values(TableReconciliationSignal) == {
        "SETTINGS_CHANGED": "settings_changed",
        "TABLE_UPDATED": "table_updated",
        "TRIGGER_NOW": "trigger_now",
        "PAUSE": "pause",
        "RESUME": "resume",
        "STOP": "stop",
        "MAINTENANCE_FINISHED": "maintenance_finished",
    }


def test_table_maintenance_signals():
    assert _values(TableMaintenanceSignal) == {
        "OPERATION_RESULT": "operation_result",
        "ADMISSION_GRANTED": "admission_granted",
    }


def test_table_maintenance_admission_signals():
    assert _values(TableMaintenanceAdmissionSignal) == {
        "ACQUIRE": "acquire",
        "RELEASE": "release",
    }


def test_table_reconciliation_activities():
    assert _values(TableReconciliationActivity) == {
        "PLAN_TABLE_MAINTENANCE": "plan_table_maintenance",
    }


def test_table_maintenance_activities():
    assert _values(TableMaintenanceActivity) == {
        "CREATE_MAINTENANCE_RUN": "create_maintenance_run",
        "SUBMIT_MAINTENANCE_OPERATION": "submit_maintenance_operation",
        "GET_MAINTENANCE_JOB_STATUS": "get_maintenance_job_status",
        "RECORD_MAINTENANCE_OPERATION_RESULT": "record_maintenance_operation_result",
        "DELETE_MAINTENANCE_JOB": "delete_maintenance_job",
        "SIGNAL_ADMISSION_ACQUIRE": "signal_admission_acquire",
        "SIGNAL_PARENT": "signal_parent",
    }


def test_table_discovery_activities():
    assert _values(TableDiscoveryActivity) == {
        "SYNC_DISCOVERED_TABLES": "sync_discovered_tables",
    }
