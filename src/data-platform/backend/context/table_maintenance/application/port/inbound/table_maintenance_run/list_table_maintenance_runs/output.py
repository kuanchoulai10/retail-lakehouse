"""Define the ListTableMaintenanceRunsUseCaseOutput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseOutput


class ListTableMaintenanceRunsUseCaseOutput(UseCaseOutput):
    """Carry the result of the request to list the maintenance runs of a table."""

    class TableMaintenanceRun(UseCaseOutput):
        """One run of the listing.

        ``content`` is what the run's job does, in primitives; ``attempts`` lists every attempt,
        oldest first, with its job, size, outcome and what followed it.
        """

        run_id: str
        table_uuid: str
        execution_ref: str
        trigger: str
        priority: str
        operation: str
        status: str
        content: dict[str, Any]
        metrics: dict[str, Any]
        error: str | None
        skip_reason: str | None
        created_at: datetime
        started_at: datetime | None
        finished_at: datetime | None
        attempts: tuple[dict[str, Any], ...]

    items: tuple[TableMaintenanceRun, ...]
