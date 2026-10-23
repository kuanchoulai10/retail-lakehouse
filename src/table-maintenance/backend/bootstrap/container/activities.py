"""Define the Activities bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from adapter.inbound.temporal.activities import (
        DiscoveryActivities,
        MaintenanceActivities,
        ReconcileActivities,
        WorkflowSignalActivities,
    )


@dataclass(frozen=True)
class Activities:
    """Hold the four activity classes the worker registers."""

    reconcile: ReconcileActivities
    maintenance: MaintenanceActivities
    discovery: DiscoveryActivities
    workflow_signal: WorkflowSignalActivities

    def callables(self) -> list[Callable[..., object]]:
        """Return every activity method, bound to its instance."""
        reconcile, maintenance = self.reconcile, self.maintenance
        signal = self.workflow_signal
        return [
            reconcile.plan_table_maintenance,
            reconcile.submit_maintenance_operation,
            reconcile.get_maintenance_job_status,
            reconcile.delete_maintenance_job,
            maintenance.create_maintenance_run,
            maintenance.record_maintenance_operation_result,
            self.discovery.sync_discovered_tables,
            signal.signal_capacity_acquire,
            signal.signal_parent,
        ]
