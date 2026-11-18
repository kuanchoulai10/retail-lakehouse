"""Define the PlanTableMaintenanceUseCaseInput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseInput


class PlanTableMaintenanceUseCaseInput(UseCaseInput):
    """Carry the request to plan the maintenance operations of a table.

    run_id names the run the plan is for: the compaction candidates a
    scheduled plan picks are claimed for it. Without it the plan picks them
    but claims none.
    """

    table_uuid: str
    now: datetime
    manual_operations: tuple[str, ...] | None = None
    run_id: str | None = None
