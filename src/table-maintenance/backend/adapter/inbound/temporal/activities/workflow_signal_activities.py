"""Define the WorkflowSignalActivities Temporal activities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from temporalio import activity
from temporalio.client import RPCError
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.service import RPCStatusCode

from adapter.temporal_contracts.activity_names import (
    SIGNAL_CAPACITY_ACQUIRE,
    SIGNAL_PARENT,
)
from adapter.temporal_contracts.capacity_acquire_signal import CapacityAcquireSignal
from adapter.temporal_contracts.capacity_limiter_input import CapacityLimiterInput
from adapter.temporal_contracts.workflow_names import CAPACITY_LIMITER_WORKFLOW
from application.domain.model.maintenance.workflow_ids import (
    CAPACITY_WORKFLOW_ID,
    SIGNAL_CAPACITY_ACQUIRE as ACQUIRE_SIGNAL_NAME,
    TASK_QUEUE,
)

if TYPE_CHECKING:
    from temporalio.client import Client


class WorkflowSignalActivities:
    """Signal other workflows on behalf of a workflow, through the Temporal client.

    The capacity limit and lease only apply when this call starts the limiter; a
    running limiter keeps the values it was started with.
    """

    def __init__(
        self,
        client: Client,
        *,
        capacity_limit: int,
        capacity_lease_seconds: int,
        task_queue: str = TASK_QUEUE,
    ) -> None:
        """Bind the client and the limiter start configuration."""
        self._client = client
        self._capacity_limit = capacity_limit
        self._capacity_lease_seconds = capacity_lease_seconds
        self._task_queue = task_queue

    @activity.defn(name=SIGNAL_CAPACITY_ACQUIRE)
    async def signal_capacity_acquire(self, request: dict[str, Any]) -> None:
        """Signal-with-start the capacity limiter with an acquire request."""
        await self._client.start_workflow(
            CAPACITY_LIMITER_WORKFLOW,
            CapacityLimiterInput(
                limit=self._capacity_limit,
                lease_seconds=self._capacity_lease_seconds,
            ),
            id=CAPACITY_WORKFLOW_ID,
            task_queue=self._task_queue,
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
            start_signal=ACQUIRE_SIGNAL_NAME,
            start_signal_args=[
                CapacityAcquireSignal(
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
