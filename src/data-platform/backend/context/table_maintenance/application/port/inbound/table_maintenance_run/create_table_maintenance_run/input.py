"""Define the CreateTableMaintenanceRunUseCaseInput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseInput


class CreateTableMaintenanceRunUseCaseInput(UseCaseInput):
    """Carry the request to create a maintenance run."""

    class Filter(UseCaseInput):
        """One where clause of a compaction, per partition spec; empty means all."""

        spec_id: int
        where: str

    run_id: str
    table_uuid: str
    execution_ref: str
    trigger: str
    operations: tuple[str, ...]
    now: datetime
    priority: str = "P3"
    filters: dict[str, tuple[Filter, ...]] = {}
