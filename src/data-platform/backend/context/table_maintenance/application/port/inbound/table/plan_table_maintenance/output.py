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
    plan for display only (``None`` likewise). ``priority`` is
    the priority the run the plan starts gets: the manual priority when one was
    given, else the table's own (P3 when the table is unknown).
    ``schedule_interval_seconds`` is how long the reconciliation waits between checks of the table
    (the policy's ``on.schedule``), and ``catalog_commit_debounce_seconds`` how long the window a
    catalog commit opens stays open before the check it calls for (``None``: the policy has no
    ``on.catalog_commit``, so commits call for no check); an unknown table answers the platform
    default's.
    """

    class Filter(UseCaseOutput):
        """One where clause of a compaction, per partition spec."""

        spec_id: int
        where: str

    class Operation(UseCaseOutput):
        """One planned operation with its filters, procedure arguments and the size it starts at."""

        operation: str
        filters: tuple[PlanTableMaintenanceUseCaseOutput.Filter, ...]
        procedure_args: dict[str, Any]
        start_size: str = "S"

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
    schedule_interval_seconds: int
    catalog_commit_debounce_seconds: int | None
    table_name: str | None
    operations: tuple[Operation, ...]
    dry_run: bool = False
    table_found: bool = True
    checks: tuple[Check, ...] = ()
    policy_id: str | None = None
    policy_name: str | None = None
    policy_version: int | None = None
    policy_target: dict[str, Any] | None = None
    priority: str = "P3"
