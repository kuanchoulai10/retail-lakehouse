"""Define the CreateTableMaintenanceRunUseCaseOutput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseOutput


class CreateTableMaintenanceRunUseCaseOutput(UseCaseOutput):
    """Carry the result of the request to create a maintenance run."""

    run_id: str
    table_uuid: str
    execution_ref: str
    trigger: str
    priority: str
    status: str
    operations: tuple[dict[str, Any], ...]
    created_at: datetime
    finished_at: datetime | None
