"""Define the TableMaintenanceActivity names."""

from __future__ import annotations

from enum import StrEnum


class TableMaintenanceActivity(StrEnum):
    """Name the activities a table maintenance workflow calls."""

    SUBMIT_MAINTENANCE_OPERATION = "submit_maintenance_operation"
    GET_MAINTENANCE_JOB_STATUS = "get_maintenance_job_status"
    RECORD_MAINTENANCE_OPERATION_RESULT = "record_maintenance_operation_result"
    DELETE_MAINTENANCE_JOB = "delete_maintenance_job"
    GET_MAINTENANCE_JOB_PROCESSES = "get_maintenance_job_processes"
    RECORD_MAINTENANCE_ATTEMPT_RUNNING = "record_maintenance_attempt_running"
    RAISE_MAINTENANCE_RUN_PRIORITY = "raise_maintenance_run_priority"
    SKIP_MAINTENANCE_RUN = "skip_maintenance_run"
    CANCEL_MAINTENANCE_RUN = "cancel_maintenance_run"
    SIGNAL_PARENT = "signal_parent"
