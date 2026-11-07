"""Define the MaintenancePlan value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from base import ValueObject

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.shared.planned_operation import (
        PlannedOperation,
    )


@dataclass(frozen=True)
class MaintenancePlan(ValueObject):
    """Hold the operations to run, in canonical execution order."""

    operations: tuple[PlannedOperation, ...] = ()

    @property
    def is_empty(self) -> bool:
        """Return whether nothing is planned."""
        return not self.operations
