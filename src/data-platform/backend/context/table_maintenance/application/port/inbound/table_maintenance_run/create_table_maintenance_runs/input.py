"""Define the CreateTableMaintenanceRunsUseCaseInput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseInput


class CreateTableMaintenanceRunsUseCaseInput(UseCaseInput):
    """Carry the request to create the maintenance runs of one plan, one run per planned operation.

    The table, the execution, the trigger, the priority and ``now`` are the plan's, shared by every run;
    ``runs`` lists each run in plan order.
    """

    class Filter(UseCaseInput):
        """One where clause of a compaction, for one partition spec."""

        spec_id: int
        where: str

    class Run(UseCaseInput):
        """One run of the plan: its id, its operation and what its procedure is called with.

        ``filters`` holds the where clauses of a compaction, one per partition spec; an empty ``filters``
        means the whole table. ``procedure_args`` holds the arguments the operation's procedure is called with.
        """

        run_id: str
        operation: str
        filters: tuple[CreateTableMaintenanceRunsUseCaseInput.Filter, ...] = ()
        procedure_args: dict[str, Any] = {}

    table_uuid: str
    execution_ref: str
    trigger: str
    now: datetime
    runs: tuple[Run, ...]
    priority: str = "P3"
