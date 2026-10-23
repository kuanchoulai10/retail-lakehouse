"""Define the MaintenanceWorkflowInput workflow contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaintenanceWorkflowInput:
    """Carry one maintenance run: its identity, its parent and its plan.

    ``plan`` is the ``plan_table_maintenance`` activity output, with ``operations``
    in canonical order.
    """

    run_id: str
    table_uuid: str
    parent_workflow_id: str
    trigger: str
    plan: dict
