"""Define the TableReconciliationActivities Temporal activities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from temporalio import activity
from temporalio.client import RPCError, WorkflowExecutionStatus
from temporalio.service import RPCStatusCode

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TableReconciliationActivity,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities.activity_payload import (
    activity_payload,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities.translate_application_errors import (
    translate_application_errors,
)
from context.table_maintenance.application.port.inbound.compaction_candidate import (
    ReleaseCompactionCandidatesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table import (
    PlanTableMaintenanceUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_reconciliation import (
    RecordTableReconciliationUseCaseInput,
)

if TYPE_CHECKING:
    from temporalio.client import Client

    from context.table_maintenance.application.port.inbound.compaction_candidate import (
        ReleaseCompactionCandidatesUseCase,
    )
    from context.table_maintenance.application.port.inbound.table import (
        PlanTableMaintenanceUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_reconciliation import (
        RecordTableReconciliationUseCase,
    )


class TableReconciliationActivities:
    """Plan and record reconciliations, release unstarted candidates and look up the maintenance run's workflow.

    Each method wraps exactly one use case, except the workflow lookup, which asks
    the Temporal client. Inputs and outputs are primitive dicts; ``now`` travels as
    an ISO-8601 string taken from ``workflow.now()``.
    """

    def __init__(
        self,
        *,
        plan: PlanTableMaintenanceUseCase,
        record: RecordTableReconciliationUseCase,
        release: ReleaseCompactionCandidatesUseCase,
        client: Client,
        attempt_deadline_seconds: int,
        max_attempts: int,
        queue_wait_limit_seconds: int,
    ) -> None:
        """Bind the use cases and the client.

        ``attempt_deadline_seconds``, ``max_attempts`` and ``queue_wait_limit_seconds``
        are the worker settings every plan carries, so the run it starts bounds each
        running attempt by the first, gives each operation that many attempts and
        lets each attempt wait in its queue for the last.
        """
        self._plan = plan
        self._record = record
        self._release = release
        self._client = client
        self._attempt_deadline_seconds = attempt_deadline_seconds
        self._max_attempts = max_attempts
        self._queue_wait_limit_seconds = queue_wait_limit_seconds

    @activity.defn(name=TableReconciliationActivity.PLAN_TABLE_MAINTENANCE)
    def plan_table_maintenance(self, request: dict[str, Any]) -> dict[str, Any]:
        """Plan a table's maintenance, with the attempt deadline, attempts and queue wait limit its run uses."""
        with translate_application_errors():
            output = self._plan.execute(PlanTableMaintenanceUseCaseInput.from_primitives(request))
        return {
            **activity_payload(output),
            "attempt_deadline_seconds": self._attempt_deadline_seconds,
            "max_attempts": self._max_attempts,
            "queue_wait_limit_seconds": self._queue_wait_limit_seconds,
        }

    @activity.defn(name=TableReconciliationActivity.RECORD_TABLE_RECONCILIATION)
    def record_table_reconciliation(self, request: dict[str, Any]) -> dict[str, Any]:
        """Record one reconciliation: why it woke, what the plan found and the run it started."""
        with translate_application_errors():
            output = self._record.execute(RecordTableReconciliationUseCaseInput.from_primitives(request))
        return activity_payload(output)

    @activity.defn(name=TableReconciliationActivity.RELEASE_COMPACTION_CANDIDATES)
    def release_compaction_candidates(self, request: dict[str, Any]) -> dict[str, Any]:
        """Hand back the compaction candidates a run claimed but never started."""
        with translate_application_errors():
            output = self._release.execute(ReleaseCompactionCandidatesUseCaseInput.from_primitives(request))
        return activity_payload(output)

    @activity.defn(name=TableReconciliationActivity.GET_WORKFLOW_RUNNING)
    async def get_workflow_running(self, request: dict[str, Any]) -> dict[str, bool]:
        """Tell whether a workflow by id is still running; a missing or closed one is not."""
        handle = self._client.get_workflow_handle(request["workflow_id"])
        try:
            description = await handle.describe()
        except RPCError as error:
            if error.status == RPCStatusCode.NOT_FOUND:
                return {"running": False}
            raise
        return {"running": description.status == WorkflowExecutionStatus.RUNNING}
