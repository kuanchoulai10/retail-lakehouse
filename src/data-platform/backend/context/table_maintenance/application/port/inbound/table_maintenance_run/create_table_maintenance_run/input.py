"""Define the CreateTableMaintenanceRunUseCaseInput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseInput


class CreateTableMaintenanceRunUseCaseInput(UseCaseInput):
    """Carry the request to create a maintenance run of one operation.

    ``filters`` holds the where clauses of a compaction, one per partition spec; an empty ``filters`` means the
    whole table. ``procedure_args`` holds the arguments the operation's procedure is called with.
    """

    class Filter(UseCaseInput):
        """One where clause of a compaction, for one partition spec."""

        spec_id: int
        where: str

    run_id: str
    table_uuid: str
    execution_ref: str
    trigger: str
    operation: str
    now: datetime
    priority: str = "P3"
    filters: tuple[Filter, ...] = ()
    procedure_args: dict[str, Any] = {}
