"""Define the OperationRun value object."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.operation_run_status import (
    OperationRunStatus,
)


@dataclass(frozen=True)
class OperationRun(ValueObject):
    """Record the progress of one maintenance operation inside a run."""

    operation: MaintenanceOperation
    status: OperationRunStatus = OperationRunStatus.PENDING
    attempts: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    job_name: str | None = None
    metrics: dict[str, int] = field(default_factory=dict)
    error: str | None = None
    expected_files: int | None = None
