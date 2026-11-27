"""Provide the build_activities function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bootstrap.container.activities import Activities
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities import (
    TableDiscoveryActivities,
    TableDiscoveryRoundActivities,
    TableMaintenanceActivities,
    TableReconciliationActivities,
)

if TYPE_CHECKING:
    from temporalio.client import Client

    from bootstrap.configs import WorkerSettings
    from bootstrap.container.use_cases import UseCases


def build_activities(use_cases: UseCases, client: Client, settings: WorkerSettings) -> Activities:
    """Build the activities; ``client`` is the worker's own, on the worker's loop."""
    return Activities(
        reconciliation=TableReconciliationActivities(
            plan=use_cases.plan_table_maintenance,
            record=use_cases.record_table_reconciliation,
            create_runs=use_cases.create_table_maintenance_runs,
            skip=use_cases.skip_table_maintenance_run,
            issue_reconciliation_id=use_cases.issue_table_reconciliation_id,
            issue_run_ids=use_cases.issue_table_maintenance_run_ids,
            client=client,
            attempt_deadline_seconds=settings.maintenance.attempt_deadline_seconds,
            max_attempts=settings.maintenance.max_attempts,
            queue_wait_limit_seconds=settings.maintenance.queue_wait_limit_seconds,
        ),
        maintenance=TableMaintenanceActivities(
            record_result=use_cases.record_table_maintenance_operation_result,
            submit=use_cases.submit_maintenance_operation,
            status=use_cases.get_maintenance_job_status,
            delete=use_cases.delete_maintenance_job,
            pods=use_cases.get_maintenance_job_processes,
            record_running=use_cases.record_maintenance_attempt_running,
            raise_priority=use_cases.raise_table_maintenance_run_priority,
            skip=use_cases.skip_table_maintenance_run,
            cancel=use_cases.cancel_table_maintenance_run,
            client=client,
            callback_base_url=settings.callback_base_url,
        ),
        discovery=TableDiscoveryActivities(sync=use_cases.sync_discovered_tables),
        discovery_round=TableDiscoveryRoundActivities(list_scanned=use_cases.list_scanned_catalogs),
    )
