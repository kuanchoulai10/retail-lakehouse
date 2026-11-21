"""Define the OperationAssessment value object."""

from __future__ import annotations

from datetime import datetime

from base import ValueObject
from context.table_maintenance.application.domain.model.shared.maintenance_operation import (
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.model.shared.measurement import (
    Measurement,
)
from context.table_maintenance.application.domain.model.shared.operation_verdict import (
    OperationVerdict,
)
from context.table_maintenance.application.domain.model.shared.planned_operation import (
    PlannedOperation,
)
from context.table_maintenance.application.domain.model.shared.size_source import (
    SizeSource,
)


class OperationAssessment(ValueObject):
    """Hold the verdict on one operation and the measures behind it.

    ``planned`` is set iff ``verdict`` is ``DUE``; a disabled operation has no
    measures and no ``next_eligible_at``. A compaction whose over-target partitions all wait for
    writes to settle is ``WAITING_FOR_WRITES``: nothing is planned, and ``next_eligible_at`` is
    the earliest time one of them is allowed to run.
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
    measurements: tuple[Measurement, ...] = ()
