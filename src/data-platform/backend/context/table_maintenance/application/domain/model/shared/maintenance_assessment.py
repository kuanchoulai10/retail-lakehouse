"""Define the MaintenanceAssessment value object."""

from __future__ import annotations

from base import ValueObject
from context.table_maintenance.application.domain.model.shared.maintenance_plan import (
    MaintenancePlan,
)
from context.table_maintenance.application.domain.model.shared.operation_assessment import (
    OperationAssessment,
)
from context.table_maintenance.application.domain.model.shared.over_target_partition import (
    OverTargetPartition,
)


class MaintenanceAssessment(ValueObject):
    """Hold one assessment per operation, in canonical execution order.

    ``over_target_partitions`` are the partitions over the compaction target with since when,
    whatever the compaction's verdict: a cooldown or a needs-attention mark does not hide them.
    It is empty when the policy has no ``rewrite_data_files`` block or compacts per table.
    """

    operations: tuple[OperationAssessment, ...] = ()
    over_target_partitions: tuple[OverTargetPartition, ...] = ()

    def plan(self) -> MaintenancePlan:
        """Return the plan made of the due operations."""
        return MaintenancePlan(operations=tuple(a.planned for a in self.operations if a.planned is not None))
