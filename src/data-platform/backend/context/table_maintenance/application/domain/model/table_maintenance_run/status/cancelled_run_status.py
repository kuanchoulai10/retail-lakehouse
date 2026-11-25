"""Define the CancelledRunStatus class."""

from __future__ import annotations

from typing import ClassVar

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_run.status.run_status import (
    RunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.run_status_name import (
    RunStatusName,
)


class CancelledRunStatus(ValueObject, RunStatus):
    """A run that was cancelled; it allows no move."""

    name: ClassVar[RunStatusName] = RunStatusName.CANCELLED
    is_terminal: ClassVar[bool] = True
