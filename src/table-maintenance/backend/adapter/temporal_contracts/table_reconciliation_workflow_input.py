"""Define the TableReconciliationWorkflowInput workflow contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableReconciliationWorkflowInput:
    """Identify the table a reconciliation workflow manages and carry its loop state.

    A fresh workflow passes only ``table_uuid``; continue-as-new carries the rest.
    ``in_flight_run_id`` is the maintenance run still awaiting its
    ``maintenance_finished`` signal, run by the workflow ``in_flight_workflow_id``
    and started at ``in_flight_started_at`` (ISO-8601) with
    ``in_flight_operation_count`` planned operations. ``pending_manual`` is a
    manual trigger not yet planned: ``None`` means none, ``[]`` means a manual run
    of every due operation, a non-empty list names the requested operations.
    ``next_plan_at`` (ISO-8601) is when the timer plans next; ``None`` means one
    ``reconcile_interval_seconds`` after start. That interval comes from the last
    plan and is also used after a failed plan. ``continue_as_new_after`` bounds
    the loop iterations per run.
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
