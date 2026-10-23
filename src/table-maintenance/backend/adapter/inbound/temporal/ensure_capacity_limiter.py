"""Define ensure_capacity_limiter, which starts the capacity limiter if needed."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.common import WorkflowIDConflictPolicy

from adapter.temporal_contracts.capacity_limiter_input import CapacityLimiterInput
from adapter.temporal_contracts.workflow_names import CAPACITY_LIMITER_WORKFLOW
from application.domain.model.maintenance.workflow_ids import (
    CAPACITY_WORKFLOW_ID,
    TASK_QUEUE,
)

if TYPE_CHECKING:
    from temporalio.client import Client


async def ensure_capacity_limiter(
    client: Client,
    *,
    limit: int,
    lease_seconds: int,
    task_queue: str = TASK_QUEUE,
) -> None:
    """Start the capacity limiter unless it is already running.

    It uses the same id, input and conflict policy as the acquire signal-with-start,
    so whichever comes first starts the limiter. A running limiter keeps the limit
    and lease it was started with.
    """
    await client.start_workflow(
        CAPACITY_LIMITER_WORKFLOW,
        CapacityLimiterInput(limit=limit, lease_seconds=lease_seconds),
        id=CAPACITY_WORKFLOW_ID,
        task_queue=task_queue,
        id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
    )
