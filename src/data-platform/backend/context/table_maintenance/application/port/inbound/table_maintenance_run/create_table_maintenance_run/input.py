"""Define the CreateTableMaintenanceRunUseCaseInput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseInput


class CreateTableMaintenanceRunUseCaseInput(UseCaseInput):
    """Carry the request to create a maintenance run."""

    run_id: str
    table_uuid: str
    execution_ref: str
    trigger: str
    operations: tuple[str, ...]
    now: datetime
