"""Temporal activity names shared by workflows and the activities they call."""

from __future__ import annotations

PLAN_TABLE_MAINTENANCE = "plan_table_maintenance"
CREATE_MAINTENANCE_RUN = "create_maintenance_run"
SUBMIT_MAINTENANCE_OPERATION = "submit_maintenance_operation"
GET_MAINTENANCE_JOB_STATUS = "get_maintenance_job_status"
RECORD_MAINTENANCE_OPERATION_RESULT = "record_maintenance_operation_result"
DELETE_MAINTENANCE_JOB = "delete_maintenance_job"
SYNC_DISCOVERED_TABLES = "sync_discovered_tables"
SIGNAL_CAPACITY_ACQUIRE = "signal_capacity_acquire"
SIGNAL_PARENT = "signal_parent"
