"""Define the TableMaintenanceActivity names."""

from __future__ import annotations

from enum import StrEnum


class TableMaintenanceActivity(StrEnum):
    """Name the activities a table maintenance workflow calls."""

    CREATE_MAINTENANCE_RUN = "create_maintenance_run"
    SUBMIT_MAINTENANCE_OPERATION = "submit_maintenance_operation"
    GET_MAINTENANCE_JOB_STATUS = "get_maintenance_job_status"
    RECORD_MAINTENANCE_OPERATION_RESULT = "record_maintenance_operation_result"
    DELETE_MAINTENANCE_JOB = "delete_maintenance_job"
    SIGNAL_ADMISSION_ACQUIRE = "signal_admission_acquire"
    SIGNAL_PARENT = "signal_parent"
