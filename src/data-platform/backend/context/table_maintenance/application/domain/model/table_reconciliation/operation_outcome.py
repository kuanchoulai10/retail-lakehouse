"""Define the OperationOutcome value object."""

from __future__ import annotations

from datetime import datetime

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import (
    ConditionCombine,
    MaintenanceOperation,
    Measurement,
)
from context.table_maintenance.application.domain.model.table_reconciliation.operation_result import (
    OperationResult,
)


class OperationOutcome(ValueObject):
    """Record what a reconciliation measured and decided for one operation."""

    operation: MaintenanceOperation
    result: OperationResult
    combine: ConditionCombine
    measurements: tuple[Measurement, ...]
    next_eligible_at: datetime | None = None
