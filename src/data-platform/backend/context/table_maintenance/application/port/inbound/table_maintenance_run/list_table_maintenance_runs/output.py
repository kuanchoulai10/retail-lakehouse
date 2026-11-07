"""Define the ListTableMaintenanceRunsUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any


@dataclass(frozen=True)
class ListTableMaintenanceRunsUseCaseOutputItem:
    """One run of the listing."""

    run_id: str
    table_uuid: str
    execution_ref: str
    trigger: str
    status: str
    operations: list[dict[str, Any]]
    created_at: datetime
    finished_at: datetime | None


@dataclass(frozen=True)
class ListTableMaintenanceRunsUseCaseOutput:
    """Carry the result of the request to list the maintenance runs of a table."""

    items: list[ListTableMaintenanceRunsUseCaseOutputItem]
