"""Define the ListTableMaintenanceRunsUseCaseOutput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseOutput


class ListTableMaintenanceRunsUseCaseOutput(UseCaseOutput):
    """Carry the result of the request to list the maintenance runs of a table."""

    class TableMaintenanceRun(UseCaseOutput):
        """One run of the listing."""

        run_id: str
        table_uuid: str
        execution_ref: str
        trigger: str
        priority: str
        status: str
        operations: tuple[dict[str, Any], ...]
        created_at: datetime
        finished_at: datetime | None

    items: tuple[TableMaintenanceRun, ...]
