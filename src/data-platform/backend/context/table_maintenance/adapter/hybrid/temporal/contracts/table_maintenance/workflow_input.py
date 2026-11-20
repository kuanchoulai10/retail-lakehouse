"""Define the TableMaintenanceWorkflowInput workflow contract."""

from __future__ import annotations

from dataclasses import dataclass

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance.default_attempt_deadline_seconds import (  # noqa: E501
    DEFAULT_ATTEMPT_DEADLINE_SECONDS,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance.default_max_attempts import (
    DEFAULT_MAX_ATTEMPTS,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance.default_queue_wait_limit_seconds import (  # noqa: E501
    DEFAULT_QUEUE_WAIT_LIMIT_SECONDS,
)


@dataclass(frozen=True)
class TableMaintenanceWorkflowInput:
    """Carry one maintenance run: its identity, its parent and its plan.

    ``plan`` is the ``plan_table_maintenance`` activity output, with ``operations``
    in canonical order. ``queue_wait_limit_seconds`` bounds how long each attempt may
    wait in its queue, from its submit until its Spark driver starts;
    ``attempt_deadline_seconds`` bounds each attempt from that start; ``max_attempts``
    is how many attempts each operation gets.
    """

    run_id: str
    table_uuid: str
    parent_workflow_id: str
    trigger: str
    plan: dict
    attempt_deadline_seconds: int = DEFAULT_ATTEMPT_DEADLINE_SECONDS
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    queue_wait_limit_seconds: int = DEFAULT_QUEUE_WAIT_LIMIT_SECONDS
