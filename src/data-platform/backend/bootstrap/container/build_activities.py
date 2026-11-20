"""Provide the build_activities function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bootstrap.container.activities import Activities
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities import (
    CompactionRoundActivities,
    TableDiscoveryActivities,
    TableMaintenanceActivities,
    TableReconciliationActivities,
)

if TYPE_CHECKING:
    from temporalio.client import Client

    from bootstrap.configs import AppSettings
    from bootstrap.container.use_cases import UseCases


def build_activities(use_cases: UseCases, client: Client, settings: AppSettings) -> Activities:
    """Build the activities; ``client`` is the worker's own, on the worker's loop."""
    return Activities(
        reconciliation=TableReconciliationActivities(
            plan=use_cases.plan_table_maintenance,
            record=use_cases.record_table_reconciliation,
            release=use_cases.release_compaction_candidates,
            client=client,
            attempt_deadline_seconds=settings.maintenance_attempt_deadline_seconds,
            max_attempts=settings.maintenance_max_attempts,
            queue_wait_limit_seconds=settings.maintenance_queue_wait_limit_seconds,
        ),
        maintenance=TableMaintenanceActivities(
            create_run=use_cases.create_table_maintenance_run,
            record_result=use_cases.record_table_maintenance_operation_result,
            submit=use_cases.submit_maintenance_operation,
            status=use_cases.get_maintenance_job_status,
            delete=use_cases.delete_maintenance_job,
            pods=use_cases.get_maintenance_job_pods,
            record_running=use_cases.record_maintenance_attempt_running,
            client=client,
            callback_base_url=settings.callback_base_url,
        ),
        discovery=TableDiscoveryActivities(sync=use_cases.sync_discovered_tables),
        compaction_round=CompactionRoundActivities(schedule=use_cases.schedule_compaction_round),
    )
