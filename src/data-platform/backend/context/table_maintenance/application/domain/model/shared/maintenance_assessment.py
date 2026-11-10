"""Define the MaintenanceAssessment value object."""

from __future__ import annotations

from base import ValueObject
from context.table_maintenance.application.domain.model.shared.maintenance_plan import (
    MaintenancePlan,
)
from context.table_maintenance.application.domain.model.shared.operation_assessment import (
    OperationAssessment,
)


class MaintenanceAssessment(ValueObject):
    """Hold one assessment per operation, in canonical execution order."""

    operations: tuple[OperationAssessment, ...] = ()

    def plan(self) -> MaintenancePlan:
        """Return the plan made of the due operations."""
        return MaintenancePlan(operations=tuple(a.planned for a in self.operations if a.planned is not None))
