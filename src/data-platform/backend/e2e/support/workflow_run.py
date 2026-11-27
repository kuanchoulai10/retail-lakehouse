"""Provide WorkflowRun, what a scenario reads of one run of a workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from temporalio.client import WorkflowExecutionStatus


@dataclass(frozen=True)
class WorkflowRun:
    """One run: its id, its status, and the id of the workflow that started it as a child (None when none did)."""

    run_id: str
    status: WorkflowExecutionStatus
    parent_id: str | None
