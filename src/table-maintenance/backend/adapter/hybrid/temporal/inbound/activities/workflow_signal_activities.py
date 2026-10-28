"""Define the WorkflowSignalActivities Temporal activities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from temporalio import activity
from temporalio.client import RPCError
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.service import RPCStatusCode

from adapter.hybrid.temporal.contracts import (
    SIGNAL_ADMISSION_ACQUIRE_ACTIVITY,
    SIGNAL_PARENT,
    AdmissionAcquireSignal,
    TableMaintenanceAdmissionInput,
    table_maintenance_admission_summary,
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW,
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID,
    SIGNAL_ADMISSION_ACQUIRE as ACQUIRE_SIGNAL_NAME,
    TASK_QUEUE,
)

if TYPE_CHECKING:
    from temporalio.client import Client


class WorkflowSignalActivities:
    """Signal other workflows on behalf of a workflow, through the Temporal client.

    The admission limit and lease only apply when this call starts the admission
    workflow; a running admission workflow keeps the values it was started with.
    """

    def __init__(
        self,
        client: Client,
        *,
        admission_limit: int,
        admission_lease_seconds: int,
    ) -> None:
        """Bind the client and the admission workflow start configuration."""
        self._client = client
        self._admission_limit = admission_limit
        self._admission_lease_seconds = admission_lease_seconds

    @activity.defn(name=SIGNAL_ADMISSION_ACQUIRE_ACTIVITY)
    async def signal_admission_acquire(self, request: dict[str, Any]) -> None:
        """Signal-with-start the admission workflow with an acquire request."""
        await self._client.start_workflow(
            TABLE_MAINTENANCE_ADMISSION_WORKFLOW,
            TableMaintenanceAdmissionInput(
                limit=self._admission_limit,
                lease_seconds=self._admission_lease_seconds,
            ),
            id=TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID,
            static_summary=table_maintenance_admission_summary(self._admission_limit),
            task_queue=TASK_QUEUE,
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
            start_signal=ACQUIRE_SIGNAL_NAME,
            start_signal_args=[
                AdmissionAcquireSignal(
                    request_id=request["request_id"],
                    requester_workflow_id=request["requester_workflow_id"],
                )
            ],
        )

    @activity.defn(name=SIGNAL_PARENT)
    async def signal_parent(self, request: dict[str, Any]) -> dict[str, bool]:
        """Signal a workflow by id; a missing workflow is reported, not raised."""
        handle = self._client.get_workflow_handle(request["workflow_id"])
        try:
            await handle.signal(request["signal"], request["arg"])
        except RPCError as error:
            if error.status == RPCStatusCode.NOT_FOUND:
                activity.logger.warning(
                    "workflow %s not found; signal %s dropped",
                    request["workflow_id"],
                    request["signal"],
                )
                return {"delivered": False}
            raise
        return {"delivered": True}
