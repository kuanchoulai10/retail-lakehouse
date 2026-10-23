"""Provide the build_activities function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from adapter.inbound.temporal.activities import (
    DiscoveryActivities,
    MaintenanceActivities,
    ReconcileActivities,
    WorkflowSignalActivities,
)
from bootstrap.container.activities import Activities
from bootstrap.container.capacity_lease_seconds import CAPACITY_LEASE_SECONDS

if TYPE_CHECKING:
    from temporalio.client import Client

    from bootstrap.configs.app_settings import AppSettings
    from bootstrap.container.use_cases import UseCases


def build_activities(
    use_cases: UseCases, client: Client, settings: AppSettings
) -> Activities:
    """Build the activities; ``client`` is the worker's own, on the worker's loop."""
    return Activities(
        reconcile=ReconcileActivities(
            plan=use_cases.plan_table_maintenance,
            submit=use_cases.submit_maintenance_operation,
            status=use_cases.get_maintenance_job_status,
            delete=use_cases.delete_maintenance_job,
            callback_base_url=settings.callback_base_url,
        ),
        maintenance=MaintenanceActivities(
            create_run=use_cases.create_maintenance_run,
            record_result=use_cases.record_maintenance_operation_result,
        ),
        discovery=DiscoveryActivities(sync=use_cases.sync_discovered_tables),
        workflow_signal=WorkflowSignalActivities(
            client,
            capacity_limit=settings.capacity_limit,
            capacity_lease_seconds=CAPACITY_LEASE_SECONDS,
            task_queue=settings.temporal.task_queue,
        ),
    )
