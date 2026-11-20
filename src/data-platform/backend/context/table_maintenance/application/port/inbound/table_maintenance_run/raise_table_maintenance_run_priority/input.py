"""Define the RaiseTableMaintenanceRunPriorityUseCaseInput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseInput


class RaiseTableMaintenanceRunPriorityUseCaseInput(UseCaseInput):
    """Carry the request to raise a maintenance run's priority.

    ``priority`` is the priority asked for; None asks for the current priority of the run's table.
    ``now`` is when the raise was asked for.
    """

    run_id: str
    priority: str | None
    now: datetime
