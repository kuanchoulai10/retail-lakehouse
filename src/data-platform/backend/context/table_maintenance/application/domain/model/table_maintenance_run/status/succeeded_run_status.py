"""Define the SucceededRunStatus class."""

from __future__ import annotations

from typing import ClassVar

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_run.status.run_status import (
    RunStatus,
)
from context.table_maintenance.application.domain.model.table_maintenance_run.status.run_status_name import (
    RunStatusName,
)


class SucceededRunStatus(ValueObject, RunStatus):
    """A run whose attempt succeeded; it allows no move."""

    name: ClassVar[RunStatusName] = RunStatusName.SUCCEEDED
    is_terminal: ClassVar[bool] = True
