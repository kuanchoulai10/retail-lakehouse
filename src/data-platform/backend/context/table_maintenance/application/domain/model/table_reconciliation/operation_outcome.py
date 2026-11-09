"""Define the OperationOutcome value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from base import ValueObject

if TYPE_CHECKING:
    from datetime import datetime

    from context.table_maintenance.application.domain.model.shared import (
        ConditionCombine,
        MaintenanceOperation,
        Measurement,
    )
    from context.table_maintenance.application.domain.model.table_reconciliation.operation_result import (
        OperationResult,
    )


@dataclass(frozen=True)
class OperationOutcome(ValueObject):
    """Record what a reconciliation measured and decided for one operation."""

    operation: MaintenanceOperation
    result: OperationResult
    combine: ConditionCombine
    measurements: tuple[Measurement, ...]
    next_eligible_at: datetime | None = None
