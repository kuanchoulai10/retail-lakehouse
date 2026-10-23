"""Define the PlanTableMaintenanceUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


@dataclass(frozen=True)
class PlanTableMaintenanceUseCaseOutputFilterItem:
    """One where clause of a compaction, per partition spec."""

    spec_id: int
    where: str


@dataclass(frozen=True)
class PlanTableMaintenanceUseCaseOutputItem:
    """One planned operation with its filters and procedure arguments."""

    operation: str
    filters: list[PlanTableMaintenanceUseCaseOutputFilterItem]
    procedure_args: dict[str, Any]


@dataclass(frozen=True)
class PlanTableMaintenanceUseCaseOutput:
    """Carry the result of the request to plan the maintenance operations of a table."""

    status: str
    reason: str | None
    reconcile_interval_seconds: int
    operations: list[PlanTableMaintenanceUseCaseOutputItem]
