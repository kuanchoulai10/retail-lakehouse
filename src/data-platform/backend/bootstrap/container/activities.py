"""Define the Activities bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.adapter.hybrid.temporal.inbound.activities import (
        TableDiscoveryActivities,
        TableMaintenanceActivities,
        TableReconciliationActivities,
    )


@dataclass(frozen=True)
class Activities:
    """Hold the activity classes the worker registers, one per workflow."""

    reconciliation: TableReconciliationActivities
    maintenance: TableMaintenanceActivities
    discovery: TableDiscoveryActivities

    def callables(self) -> list[Callable[..., object]]:
        """Return every activity method, bound to its instance."""
        reconciliation, maintenance = self.reconciliation, self.maintenance
        return [
            reconciliation.plan_table_maintenance,
            reconciliation.record_table_reconciliation,
            reconciliation.get_workflow_running,
            maintenance.create_table_maintenance_run,
            maintenance.record_table_maintenance_operation_result,
            maintenance.submit_maintenance_operation,
            maintenance.get_maintenance_job_status,
            maintenance.delete_maintenance_job,
            maintenance.get_maintenance_job_pods,
            maintenance.record_maintenance_attempt_running,
            maintenance.raise_table_maintenance_run_priority,
            maintenance.skip_table_maintenance_run,
            maintenance.signal_parent,
            self.discovery.sync_discovered_tables,
        ]
