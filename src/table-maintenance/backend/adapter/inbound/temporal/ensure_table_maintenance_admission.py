"""Define ensure_table_maintenance_admission, which starts the admission workflow if needed."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.common import WorkflowIDConflictPolicy

from adapter.temporal_contracts.table_maintenance_admission_input import (
    TableMaintenanceAdmissionInput,
)
from adapter.temporal_contracts.workflow_names import (
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW,
)
from application.domain.model.maintenance.workflow_ids import (
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID,
    TASK_QUEUE,
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
        TableMaintenanceAdmissionInput(limit=limit, lease_seconds=lease_seconds),
        id=TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID,
        task_queue=TASK_QUEUE,
        id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
    )
