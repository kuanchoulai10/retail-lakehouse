"""Define the GetTableMaintenanceRunUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any


@dataclass(frozen=True)
class GetTableMaintenanceRunUseCaseOutput:
    """Carry the result of the request to get one maintenance run."""

    run_id: str
    table_uuid: str
    execution_ref: str
    trigger: str
    status: str
    operations: list[dict[str, Any]]
    created_at: datetime
    finished_at: datetime | None
