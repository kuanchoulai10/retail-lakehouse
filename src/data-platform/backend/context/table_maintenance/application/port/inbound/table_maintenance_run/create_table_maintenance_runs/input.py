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

    class Run(UseCaseInput):
        """One run of the plan: its id, its operation and what its job does.

        ``content`` is the job content the plan built, in primitives.
        """

        run_id: str
        operation: str
        content: dict[str, Any]

    table_uuid: str
    execution_ref: str
    trigger: str
    now: datetime
    runs: tuple[Run, ...]
    priority: str
