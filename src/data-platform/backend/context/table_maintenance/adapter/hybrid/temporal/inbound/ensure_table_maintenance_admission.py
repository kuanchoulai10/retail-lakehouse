"""Define ensure_table_maintenance_admission, which starts the admission workflow if needed."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.common import WorkflowIDConflictPolicy

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance_admission import (
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW,
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID,
    TableMaintenanceAdmissionWorkflowInput,
    table_maintenance_admission_summary,
)

if TYPE_CHECKING:
    from temporalio.client import Client


async def ensure_table_maintenance_admission(
    client: Client,
    *,
    limit: int,
    lease_seconds: int,
) -> None:
    """Start the admission workflow unless it is already running.

    It uses the same id, input and conflict policy as the acquire signal-with-start,
    so whichever comes first starts the admission workflow. A running admission
    workflow keeps the limit and lease it was started with.
    """
    await client.start_workflow(
        TABLE_MAINTENANCE_ADMISSION_WORKFLOW,
        TableMaintenanceAdmissionWorkflowInput(limit=limit, lease_seconds=lease_seconds),
        id=TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID,
        static_summary=table_maintenance_admission_summary(limit),
        task_queue=TASK_QUEUE,
        id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
    )
