"""Define the OperationAssessment value object."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from application.domain.model.shared.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.shared.operation_verdict import OperationVerdict
from application.domain.model.shared.planned_operation import PlannedOperation
from application.domain.model.shared.size_source import SizeSource
from base import ValueObject


@dataclass(frozen=True)
class OperationAssessment(ValueObject):
    """Hold the verdict on one operation and the measures behind it.

    ``planned`` is set iff ``verdict`` is ``DUE``; a disabled operation has no
    measures and no ``next_eligible_at``.
    """

    operation: MaintenanceOperation
    verdict: OperationVerdict
    measured: int | None = None
    threshold: int | None = None
    next_eligible_at: datetime | None = None
    qualifying_partitions: int | None = None
    size_bytes: int | None = None
    size_source: SizeSource | None = None
    planned: PlannedOperation | None = None
