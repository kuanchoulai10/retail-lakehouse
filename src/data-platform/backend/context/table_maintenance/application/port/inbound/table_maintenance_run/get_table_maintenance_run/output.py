"""Define the GetTableMaintenanceRunUseCaseOutput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseOutput


class GetTableMaintenanceRunUseCaseOutput(UseCaseOutput):
    """Carry the result of the request to get one maintenance run."""

    run_id: str
    table_uuid: str
    execution_ref: str
    trigger: str
    status: str
    operations: tuple[dict[str, Any], ...]
    created_at: datetime
    finished_at: datetime | None
