"""Define the PlanTableMaintenanceUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any


@dataclass(frozen=True)
class PlanTableMaintenanceUseCaseOutputFilterItem:
    """One where clause of a compaction, per partition spec."""

    spec_id: int
    where: str


@dataclass(frozen=True)
class PlanTableMaintenanceUseCaseOutputCandidatePartitionItem:
    """One compaction candidate a planned compaction takes, by spec id and partition values.

    Spec id -1 with no values stands for the whole table.
    """

    spec_id: int
    values: list[Any]


@dataclass(frozen=True)
class PlanTableMaintenanceUseCaseOutputItem:
    """One planned operation with its filters and procedure arguments.

    candidate_partitions are the compaction candidates a scheduled
    compaction takes, best first (empty for any other operation and for a
    manual run).
    """

    operation: str
    filters: list[PlanTableMaintenanceUseCaseOutputFilterItem]
    procedure_args: dict[str, Any]
    start_size: str = "S"
    candidate_partitions: list[PlanTableMaintenanceUseCaseOutputCandidatePartitionItem] = field(default_factory=list)


@dataclass(frozen=True)
class PlanTableMaintenanceUseCaseOutputMeasurementItem:
    """One measured value of an operation check, with its threshold when it is a condition."""

    key: str
    observed: int
    unit: str
    threshold: int | None
    comparison: str | None
    met: bool | None


@dataclass(frozen=True)
class PlanTableMaintenanceUseCaseOutputCheckItem:
    """The verdict on one operation and the measurements behind it."""

    operation: str
    verdict: str
    measurements: list[PlanTableMaintenanceUseCaseOutputMeasurementItem]
    next_eligible_at: datetime | None


@dataclass(frozen=True)
class PlanTableMaintenanceUseCaseOutput:
    """Carry the result of the request to plan the maintenance operations of a table.

    ``table_name`` is the fully qualified ``catalog.namespace.table`` name, or
    ``None`` when the table is not managed (any more). ``policy_name``,
    ``policy_version`` and ``policy_target`` name the maintenance policy that
    was applied and where it is attached (``None`` for the default with nothing
    attached); they are ``None`` only when the table is unknown. ``next_check_at``
    is when a due compaction whose candidates are all held by a filter may find
    one free (None otherwise), so the caller can look again then.
    """

    status: str
    reason: str | None
    reconcile_interval_seconds: int
    table_name: str | None
    operations: list[PlanTableMaintenanceUseCaseOutputItem]
    dry_run: bool = False
    table_found: bool = True
    checks: list[PlanTableMaintenanceUseCaseOutputCheckItem] = field(default_factory=list)
    policy_name: str | None = None
    policy_version: int | None = None
    policy_target: dict[str, Any] | None = None
    next_check_at: datetime | None = None
