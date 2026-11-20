"""Pin the names Temporal stores in workflow histories and schedules.

Workflow types, signal names, activity names, the task queue and the fixed IDs
travel over the wire and are recorded in running histories, so moving or
renaming the Python symbols must never change these strings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.adapter.hybrid.temporal.contracts.compaction_round import (
    COMPACTION_ROUND_SCHEDULE_ID,
    COMPACTION_ROUND_WORKFLOW,
    CompactionRoundActivity,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
    TableSearchAttribute,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_SCHEDULE_ID_PREFIX,
    TABLE_DISCOVERY_WORKFLOW,
    TableDiscoveryActivity,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    DEFAULT_START_SIZE,
    TABLE_MAINTENANCE_WORKFLOW,
    MaintenanceAttemptEnding,
    MaintenanceFailureClass,
    MaintenanceNextStep,
    TableMaintenanceActivity,
    TableMaintenanceSignal,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TABLE_RECONCILIATION_WORKFLOW,
    TableReconciliationActivity,
    TableReconciliationSignal,
)
from context.table_maintenance.application.domain.model.shared import ComputeSize
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    AttemptEnding,
    FailureClass,
    NextStep,
)

if TYPE_CHECKING:
    from enum import StrEnum


def _values(enum: type[StrEnum]) -> dict[str, str]:
    return {member.name: member.value for member in enum}


def test_workflow_type_names():
    """The workflow type names are the stable wire names."""
    assert TABLE_DISCOVERY_WORKFLOW == "TableDiscoveryWorkflow"
    assert TABLE_RECONCILIATION_WORKFLOW == "TableReconciliationWorkflow"
    assert TABLE_MAINTENANCE_WORKFLOW == "TableMaintenanceWorkflow"
    assert COMPACTION_ROUND_WORKFLOW == "CompactionRoundWorkflow"


def test_task_queue_and_fixed_ids():
    """The task queue name and the fixed workflow and schedule ids are the stable wire values."""
    assert TASK_QUEUE == "table-maintenance"
    assert TABLE_DISCOVERY_SCHEDULE_ID_PREFIX == "table-discovery:catalog="
    assert COMPACTION_ROUND_SCHEDULE_ID == "compaction-rounds"


def test_table_reconciliation_signals():
    """The table reconciliation signal names are the stable wire names."""
    assert _values(TableReconciliationSignal) == {
        "POLICY_CHANGED": "policy_changed",
        "TABLE_UPDATED": "table_updated",
        "TRIGGER_NOW": "trigger_now",
        "STOP": "stop",
        "MAINTENANCE_FINISHED": "maintenance_finished",
        "RECONCILE_NOW": "reconcile_now",
        "TABLE_SEEN": "table_seen",
        "COMPACTION_GRANTED": "compaction_granted",
    }


def test_table_maintenance_signals():
    """The table maintenance signal names are the stable wire names."""
    assert _values(TableMaintenanceSignal) == {
        "OPERATION_RESULT": "operation_result",
        "RAISE_PRIORITY": "raise_priority",
    }


def test_table_reconciliation_activities():
    """The table reconciliation activity names are the stable wire names."""
    assert _values(TableReconciliationActivity) == {
        "PLAN_TABLE_MAINTENANCE": "plan_table_maintenance",
        "RECORD_TABLE_RECONCILIATION": "record_table_reconciliation",
        "GET_WORKFLOW_RUNNING": "get_workflow_running",
        "RELEASE_COMPACTION_CANDIDATES": "release_compaction_candidates",
    }


def test_table_maintenance_activities():
    """The table maintenance activity names are the stable wire names."""
    assert _values(TableMaintenanceActivity) == {
        "CREATE_MAINTENANCE_RUN": "create_maintenance_run",
        "SUBMIT_MAINTENANCE_OPERATION": "submit_maintenance_operation",
        "GET_MAINTENANCE_JOB_STATUS": "get_maintenance_job_status",
        "RECORD_MAINTENANCE_OPERATION_RESULT": "record_maintenance_operation_result",
        "DELETE_MAINTENANCE_JOB": "delete_maintenance_job",
        "GET_MAINTENANCE_JOB_PODS": "get_maintenance_job_pods",
        "RECORD_MAINTENANCE_ATTEMPT_RUNNING": "record_maintenance_attempt_running",
        "RAISE_MAINTENANCE_RUN_PRIORITY": "raise_maintenance_run_priority",
        "SIGNAL_PARENT": "signal_parent",
    }


def test_table_discovery_activities():
    """The table discovery activity names are the stable wire names."""
    assert _values(TableDiscoveryActivity) == {
        "SYNC_DISCOVERED_TABLES": "sync_discovered_tables",
    }


def test_compaction_round_activities():
    """The compaction round activity names are the stable wire names."""
    assert _values(CompactionRoundActivity) == {
        "SCHEDULE_COMPACTION_ROUND": "schedule_compaction_round",
    }


def test_table_search_attribute_names():
    """The table search attribute names are the names registered on the Temporal namespace."""
    assert _values(TableSearchAttribute) == {
        "TABLE_UUID": "TableUuid",
        "TABLE_NAME": "TableName",
        "MAINTENANCE_OPERATIONS": "MaintenanceOperations",
        "MAINTENANCE_TRIGGER": "MaintenanceTrigger",
        "GRANTED_TABLE_UUIDS": "GrantedTableUuids",
    }


def test_maintenance_attempt_endings():
    """The attempt endings sent to the record activity are the stable wire values."""
    assert _values(MaintenanceAttemptEnding) == {
        "RESULT": "result",
        "JOB_FAILED": "job_failed",
        "TIMED_OUT": "timed_out",
        "MISSING": "missing",
        "CANCELLED": "cancelled",
        "SUBMIT_FAILED": "submit_failed",
        "QUEUE_TIMED_OUT": "queue_timed_out",
    }


def test_maintenance_next_steps():
    """The next steps the record activity replies with are the stable wire values."""
    assert _values(MaintenanceNextStep) == {
        "DONE": "done",
        "RETRY_LARGER": "retry_larger",
        "RETRY_SAME": "retry_same",
        "NEEDS_ATTENTION": "needs_attention",
        "ATTEMPTS_USED": "attempts_used",
        "NOT_RETRIED": "not_retried",
        "CANCELLED": "cancelled",
        "STILL_RUNNING": "still_running",
    }


def test_maintenance_failure_classes():
    """The failure classes the record activity replies with are the stable wire values."""
    assert _values(MaintenanceFailureClass) == {
        "OOM": "oom",
        "TIMEOUT": "timeout",
        "COMMIT_CONFLICT": "commit_conflict",
        "PERMANENT": "permanent",
        "CANCELLED": "cancelled",
        "OTHER": "other",
        "QUEUE_TIMEOUT": "queue_timeout",
    }


def test_default_start_size():
    """A plan without a start size starts at S."""
    assert DEFAULT_START_SIZE == "S"


def test_domain_and_contract_values_agree():
    """The contract enums carry exactly the domain's values, so the record activity understands both sides."""
    assert {e.value for e in AttemptEnding} == {e.value for e in MaintenanceAttemptEnding}
    assert {e.value for e in NextStep} == {e.value for e in MaintenanceNextStep}
    assert {e.value for e in FailureClass} == {e.value for e in MaintenanceFailureClass}
    assert DEFAULT_START_SIZE in {s.value for s in ComputeSize}
