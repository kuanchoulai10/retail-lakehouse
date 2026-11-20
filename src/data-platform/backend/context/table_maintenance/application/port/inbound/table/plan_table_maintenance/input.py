"""Define the PlanTableMaintenanceUseCaseInput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseInput


class PlanTableMaintenanceUseCaseInput(UseCaseInput):
    """Carry the request to plan the maintenance operations of a table.

    manual_priority is the priority a manual plan sets for its run; without it
    the plan carries the table's own.
    """

    table_uuid: str
    now: datetime
    manual_operations: tuple[str, ...] | None = None
    manual_priority: str | None = None
