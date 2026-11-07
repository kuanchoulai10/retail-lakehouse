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
        WorkflowSignalActivities,
    )


@dataclass(frozen=True)
class Activities:
    """Hold the four activity classes the worker registers."""

    reconciliation: TableReconciliationActivities
    maintenance: TableMaintenanceActivities
    discovery: TableDiscoveryActivities
    workflow_signal: WorkflowSignalActivities

    def callables(self) -> list[Callable[..., object]]:
        """Return every activity method, bound to its instance."""
        reconciliation, maintenance = self.reconciliation, self.maintenance
        signal = self.workflow_signal
        return [
            reconciliation.plan_table_maintenance,
            reconciliation.submit_maintenance_operation,
            reconciliation.get_maintenance_job_status,
            reconciliation.delete_maintenance_job,
            maintenance.create_table_maintenance_run,
            maintenance.record_table_maintenance_operation_result,
            self.discovery.sync_discovered_tables,
            signal.signal_admission_acquire,
            signal.signal_parent,
        ]
