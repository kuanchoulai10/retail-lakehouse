"""Define the TableMaintenanceWorkflowInput workflow contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableMaintenanceWorkflowInput:
    """Carry the maintenance runs of one plan: their identities, their parent and their plan.

    ``plan`` is the ``plan_table_maintenance`` activity output, with ``operations``
    in canonical order. ``run_ids`` holds one run id per planned operation, in the same order: the
    workflow runs each operation as its own run. ``queue_wait_limit_seconds`` bounds how long each attempt may
    wait in its queue, from its submit until its Spark driver starts;
    ``attempt_deadline_seconds`` bounds each attempt from that start; ``max_attempts``
    is how many attempts each operation gets.
    """

    run_ids: list[str]
    table_uuid: str
    parent_workflow_id: str
    trigger: str
    plan: dict
    attempt_deadline_seconds: int
    max_attempts: int
    queue_wait_limit_seconds: int
