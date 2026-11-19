"""Define the PlanTableMaintenanceUseCaseOutput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseOutput


class PlanTableMaintenanceUseCaseOutput(UseCaseOutput):
    """Carry the result of the request to plan the maintenance operations of a table.

    ``table_name`` is the fully qualified ``catalog.namespace.table`` name, or
    ``None`` when the table is not managed (any more). ``policy_id`` (the
    policy's ``mp-`` id, not its name, which may change), ``policy_version`` and
    ``policy_target`` point at the maintenance policy that
    was applied and where it is attached (``None`` for the default with nothing
    attached); they are ``None`` only when the table is unknown. ``policy_name`` is
    that policy's name at planning time, carried to the records written under the
    plan for display only (``None`` likewise). ``next_check_at``
    is when a due compaction whose candidates are all held by a filter may find
    one free (None otherwise), so the caller can look again then. ``priority`` is
    the priority the run the plan starts gets: the manual priority when one was
    given, else the table's own (P3 when the table is unknown).
    """

    class Filter(UseCaseOutput):
        """One where clause of a compaction, per partition spec."""

        spec_id: int
        where: str

    class CandidatePartition(UseCaseOutput):
        """One compaction candidate a planned compaction takes, by spec id and partition values.

        Spec id -1 with no values stands for the whole table.
        """

        spec_id: int
        values: tuple[Any, ...]

    class Operation(UseCaseOutput):
        """One planned operation with its filters and procedure arguments.

        ``candidate_partitions`` are the compaction candidates a scheduled
        compaction takes, best first (empty for any other operation and for a
        manual run). ``filter_sets`` are the filters of ever fewer of them, for
        retries after running out of memory: all of them (equal to ``filters``),
        the best half, the best quarter (rounded up, each set once); empty when
        the compaction cannot be narrowed (a whole table, or no candidates).
        """

        operation: str
        filters: tuple[PlanTableMaintenanceUseCaseOutput.Filter, ...]
        procedure_args: dict[str, Any]
        start_size: str = "S"
        candidate_partitions: tuple[PlanTableMaintenanceUseCaseOutput.CandidatePartition, ...] = ()
        filter_sets: tuple[tuple[PlanTableMaintenanceUseCaseOutput.Filter, ...], ...] = ()

    class Measurement(UseCaseOutput):
        """One measured value of an operation check, with its threshold when it is a condition."""

        key: str
        observed: int
        unit: str
        threshold: int | None
        comparison: str | None
        met: bool | None

    class Check(UseCaseOutput):
        """The verdict on one operation and the measurements behind it."""

        operation: str
        verdict: str
        measurements: tuple[PlanTableMaintenanceUseCaseOutput.Measurement, ...]
        next_eligible_at: datetime | None

    status: str
    reason: str | None
    reconcile_interval_seconds: int
    table_name: str | None
    operations: tuple[Operation, ...]
    dry_run: bool = False
    table_found: bool = True
    checks: tuple[Check, ...] = ()
    policy_id: str | None = None
    policy_name: str | None = None
    policy_version: int | None = None
    policy_target: dict[str, Any] | None = None
    next_check_at: datetime | None = None
    priority: str = "P3"
