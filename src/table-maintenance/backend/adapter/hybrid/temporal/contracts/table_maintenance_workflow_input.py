"""Define the TableMaintenanceWorkflowInput workflow contract."""

from __future__ import annotations

from dataclasses import dataclass

from adapter.hybrid.temporal.contracts.default_attempt_deadline_seconds import (
    DEFAULT_ATTEMPT_DEADLINE_SECONDS,
)


@dataclass(frozen=True)
class TableMaintenanceWorkflowInput:
    """Carry one maintenance run: its identity, its parent and its plan.

    ``plan`` is the ``plan_table_maintenance`` activity output, with ``operations``
    in canonical order. ``attempt_deadline_seconds`` bounds each attempt, measured
    from its submit.
    """

    run_id: str
    table_uuid: str
    parent_workflow_id: str
    trigger: str
    plan: dict
    attempt_deadline_seconds: int = DEFAULT_ATTEMPT_DEADLINE_SECONDS
