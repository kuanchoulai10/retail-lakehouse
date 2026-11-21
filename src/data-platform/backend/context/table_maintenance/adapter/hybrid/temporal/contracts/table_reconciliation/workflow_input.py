"""Define the TableReconciliationWorkflowInput workflow contract."""

from __future__ import annotations

from dataclasses import dataclass

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    DEFAULT_ATTEMPT_DEADLINE_SECONDS,
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_QUEUE_WAIT_LIMIT_SECONDS,
)


@dataclass(frozen=True)
class TableReconciliationWorkflowInput:
    """Identify the table a reconciliation workflow manages and carry its loop state.

    A fresh workflow passes only ``table_uuid``; continue-as-new carries the rest.
    ``in_flight_run_ids`` are the maintenance runs, one per planned operation, whose workflow has not sent its
    ``maintenance_finished`` signal, run by the workflow ``in_flight_workflow_id``
    and started at ``in_flight_started_at`` (ISO-8601) with
    ``in_flight_operation_count`` planned operations, each attempt allowed to wait
    ``in_flight_queue_wait_limit_seconds`` in its queue and bounded by
    ``in_flight_attempt_deadline_seconds`` once it runs, and each operation given
    ``in_flight_max_attempts``. ``pending_manual`` is a
    manual trigger not yet planned: ``None`` means none, ``[]`` means a manual run
    of every due operation, a non-empty list names the requested operations.
    ``pending_manual_priority`` is the priority that trigger asked for (``None``: the table's own).
    ``raised_manual`` and ``raised_manual_priority`` keep, in the same shape, the manual trigger
    the run in flight was asked to raise its priority for (``None``: none), so it can be planned
    after the run should the run report the raise unapplied. ``raises_delivered`` counts the raise
    signals delivered to the run in flight, so a run that reports fewer received gives that trigger
    back too. ``closing_workflow_id`` is the
    workflow of a run that reported but may not have closed yet (``None``: none); the next run is
    not started under that id until it closed or the closing bound passed.
    ``next_plan_at`` (ISO-8601) is when the timer plans next; ``None`` means one
    ``schedule_interval_seconds`` after start. That interval and
    ``catalog_commit_debounce_seconds`` (``None``: commits call for no check) come from
    the last plan, are kept after a failed plan, and before the first plan are the
    platform default's. ``commit_window_closes_at`` (ISO-8601) is the end of the open
    catalog commit window (``None``: none open) and ``pending_commits`` the commits it
    holds, not yet counted as wake reasons. ``continue_as_new_after`` bounds
    the loop iterations per run. ``wake_reasons`` counts, per reason, the wakes
    not yet taken by a plan (``None`` means none), so the next reconciliation
    records them.
    """

    table_uuid: str
    in_flight_run_ids: list[str] | None = None
    in_flight_workflow_id: str | None = None
    in_flight_started_at: str | None = None
    in_flight_operation_count: int = 0
    pending_manual: list[str] | None = None
    next_plan_at: str | None = None
    schedule_interval_seconds: int = 3600
    continue_as_new_after: int = 200
    wake_reasons: dict[str, int] | None = None
    in_flight_attempt_deadline_seconds: int = DEFAULT_ATTEMPT_DEADLINE_SECONDS
    in_flight_max_attempts: int = DEFAULT_MAX_ATTEMPTS
    in_flight_queue_wait_limit_seconds: int = DEFAULT_QUEUE_WAIT_LIMIT_SECONDS
    pending_manual_priority: str | None = None
    raised_manual: list[str] | None = None
    raised_manual_priority: str | None = None
    closing_workflow_id: str | None = None
    raises_delivered: int = 0
    catalog_commit_debounce_seconds: int | None = 300
    commit_window_closes_at: str | None = None
    pending_commits: int = 0
