"""Provide the build_activities function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bootstrap.container.activities import Activities
from bootstrap.container.admission_lease_seconds import ADMISSION_LEASE_SECONDS
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities import (
    TableDiscoveryActivities,
    TableMaintenanceActivities,
    TableReconciliationActivities,
    WorkflowSignalActivities,
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
            submit=use_cases.submit_maintenance_operation,
            status=use_cases.get_maintenance_job_status,
            delete=use_cases.delete_maintenance_job,
            callback_base_url=settings.callback_base_url,
        ),
        maintenance=TableMaintenanceActivities(
            create_run=use_cases.create_table_maintenance_run,
            record_result=use_cases.record_table_maintenance_operation_result,
        ),
        discovery=TableDiscoveryActivities(sync=use_cases.sync_discovered_tables),
        workflow_signal=WorkflowSignalActivities(
            client,
            admission_limit=settings.admission_limit,
            admission_lease_seconds=ADMISSION_LEASE_SECONDS,
        ),
    )
