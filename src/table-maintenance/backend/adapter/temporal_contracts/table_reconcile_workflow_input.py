"""Define the TableReconcileWorkflowInput workflow contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableReconcileWorkflowInput:
    """Identify the table a reconcile workflow manages and carry its loop state.

    A fresh workflow passes only ``table_uuid``; continue-as-new carries the rest.
    ``in_flight_run_id`` is the maintenance run still awaiting its
    ``maintenance_finished`` signal, started at ``in_flight_started_at`` (ISO-8601)
    with ``in_flight_operation_count`` planned operations. ``pending_manual`` is a
    manual trigger not yet planned: ``None`` means none, ``[]`` means a manual run
    of every due operation, a non-empty list names the requested operations.
    ``next_plan_at`` (ISO-8601) is when the timer plans next; ``None`` means one
    hour after start. ``continue_as_new_after`` bounds the loop iterations per run.
    """

    table_uuid: str
    in_flight_run_id: str | None = None
    in_flight_started_at: str | None = None
    in_flight_operation_count: int = 0
    pending_manual: list[str] | None = None
    next_plan_at: str | None = None
    continue_as_new_after: int = 200
