"""Define the OperationOutcome value object."""

from __future__ import annotations

from datetime import datetime

from pydantic import model_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    Measurement,
)
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    TableMaintenanceRunId,
)
from context.table_maintenance.application.domain.model.table_reconciliation.operation_result import (
    OperationResult,
)


class OperationOutcome(ValueObject):
    """Record what a reconciliation measured and decided for one operation.

    ``run_id`` is the ``mr-`` id of the maintenance run the operation started, set exactly when
    ``result`` is ``STARTED``.
    """

    operation: MaintenanceOperation
    result: OperationResult
    measurements: tuple[Measurement, ...]
    next_eligible_at: datetime | None = None
    run_id: TableMaintenanceRunId | None = None

    @model_validator(mode="after")
    def _a_run_belongs_to_a_started_operation(self) -> OperationOutcome:
        """Reject a run on an operation that did not start, and a started operation without one."""
        started = self.result is OperationResult.STARTED
        if self.run_id is not None and not started:
            raise ValueError("only a started operation has a run")
        if started and self.run_id is None:
            raise ValueError("a started operation names its run")
        return self
