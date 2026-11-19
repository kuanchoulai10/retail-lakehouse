"""Define the TableReconciliationWorkflowInput workflow contract."""

from __future__ import annotations

from dataclasses import dataclass

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    DEFAULT_ATTEMPT_DEADLINE_SECONDS,
    DEFAULT_MAX_ATTEMPTS,
)


@dataclass(frozen=True)
class TableReconciliationWorkflowInput:
    """Identify the table a reconciliation workflow manages and carry its loop state.

    A fresh workflow passes only ``table_uuid``; continue-as-new carries the rest.
    ``in_flight_run_id`` is the maintenance run still awaiting its
    ``maintenance_finished`` signal, run by the workflow ``in_flight_workflow_id``
    and started at ``in_flight_started_at`` (ISO-8601) with
    ``in_flight_operation_count`` planned operations, each attempt bounded by
    ``in_flight_attempt_deadline_seconds`` and each operation given
    ``in_flight_max_attempts``. ``pending_manual`` is a
    manual trigger not yet planned: ``None`` means none, ``[]`` means a manual run
    of every due operation, a non-empty list names the requested operations.
    ``pending_manual_priority`` is the priority that trigger asked for (``None``: the table's own).
    ``next_plan_at`` (ISO-8601) is when the timer plans next; ``None`` means one
    ``reconcile_interval_seconds`` after start. That interval comes from the last
    plan and is also used after a failed plan. ``continue_as_new_after`` bounds
    the loop iterations per run. ``wake_reasons`` counts, per reason, the wakes
    not yet taken by a plan (``None`` means none), so the next reconciliation
    records them.
    """

    table_uuid: str
    in_flight_run_id: str | None = None
    in_flight_workflow_id: str | None = None
    in_flight_started_at: str | None = None
    in_flight_operation_count: int = 0
    pending_manual: list[str] | None = None
    next_plan_at: str | None = None
    reconcile_interval_seconds: int = 3600
    continue_as_new_after: int = 200
    wake_reasons: dict[str, int] | None = None
    in_flight_attempt_deadline_seconds: int = DEFAULT_ATTEMPT_DEADLINE_SECONDS
    in_flight_max_attempts: int = DEFAULT_MAX_ATTEMPTS
    pending_manual_priority: str | None = None
