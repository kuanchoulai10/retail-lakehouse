"""Define the TableReconciliationActivities Temporal activities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from temporalio import activity

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    TableMaintenanceActivity,
)
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
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    DeleteMaintenanceJobUseCaseInput,
    GetMaintenanceJobPodsUseCaseInput,
    GetMaintenanceJobStatusUseCaseInput,
    SubmitMaintenanceOperationUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_reconciliation import (
    RecordTableReconciliationUseCaseInput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.compaction_candidate import (
        ReleaseCompactionCandidatesUseCase,
    )
    from context.table_maintenance.application.port.inbound.table import (
        PlanTableMaintenanceUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_maintenance_run import (
        DeleteMaintenanceJobUseCase,
        GetMaintenanceJobPodsUseCase,
        GetMaintenanceJobStatusUseCase,
        SubmitMaintenanceOperationUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_reconciliation import (
        RecordTableReconciliationUseCase,
    )


class TableReconciliationActivities:
    """Plan and record reconciliations, release unstarted candidates, run maintenance Spark jobs and read their pods.

    Each method wraps exactly one use case. Inputs and outputs are primitive dicts;
    ``now`` travels as an ISO-8601 string taken from ``workflow.now()``.
    """

    def __init__(
        self,
        *,
        plan: PlanTableMaintenanceUseCase,
        record: RecordTableReconciliationUseCase,
        release: ReleaseCompactionCandidatesUseCase,
        submit: SubmitMaintenanceOperationUseCase,
        status: GetMaintenanceJobStatusUseCase,
        delete: DeleteMaintenanceJobUseCase,
        pods: GetMaintenanceJobPodsUseCase,
        callback_base_url: str,
        attempt_deadline_seconds: int,
        max_attempts: int,
    ) -> None:
        """Bind the use cases and the base URL Spark jobs call back to.

        ``attempt_deadline_seconds`` and ``max_attempts`` are the worker settings
        every plan carries, so the run it starts bounds each attempt by the first
        and gives each operation that many attempts.
        """
        self._plan = plan
        self._record = record
        self._release = release
        self._submit = submit
        self._status = status
        self._delete = delete
        self._pods = pods
        self._callback_base_url = callback_base_url
        self._attempt_deadline_seconds = attempt_deadline_seconds
        self._max_attempts = max_attempts

    @activity.defn(name=TableReconciliationActivity.PLAN_TABLE_MAINTENANCE)
    def plan_table_maintenance(self, request: dict[str, Any]) -> dict[str, Any]:
        """Plan the maintenance operations of a table, with the attempt deadline and attempts its run uses."""
        with translate_application_errors():
            output = self._plan.execute(PlanTableMaintenanceUseCaseInput.from_primitives(request))
        return {
            **activity_payload(output),
            "attempt_deadline_seconds": self._attempt_deadline_seconds,
            "max_attempts": self._max_attempts,
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

    @activity.defn(name=TableMaintenanceActivity.SUBMIT_MAINTENANCE_OPERATION)
    def submit_maintenance_operation(self, request: dict[str, Any]) -> dict[str, Any]:
        """Start one attempt of an operation and submit its Spark job, calling back to this worker's base URL."""
        with translate_application_errors():
            output = self._submit.execute(
                SubmitMaintenanceOperationUseCaseInput.from_primitives(
                    {**request, "callback_base_url": self._callback_base_url}
                )
            )
        return activity_payload(output)

    @activity.defn(name=TableMaintenanceActivity.GET_MAINTENANCE_JOB_STATUS)
    def get_maintenance_job_status(self, request: dict[str, Any]) -> dict[str, Any]:
        """Report the state of a Spark maintenance job."""
        with translate_application_errors():
            output = self._status.execute(GetMaintenanceJobStatusUseCaseInput.from_primitives(request))
        return activity_payload(output)

    @activity.defn(name=TableMaintenanceActivity.DELETE_MAINTENANCE_JOB)
    def delete_maintenance_job(self, request: dict[str, Any]) -> dict[str, Any]:
        """Delete the Spark job of one ``(run_id, operation, attempt)``."""
        with translate_application_errors():
            output = self._delete.execute(DeleteMaintenanceJobUseCaseInput.from_primitives(request))
        return activity_payload(output)

    @activity.defn(name=TableMaintenanceActivity.GET_MAINTENANCE_JOB_PODS)
    def get_maintenance_job_pods(self, request: dict[str, Any]) -> dict[str, Any]:
        """Report the live pods of the Spark job of one ``(run_id, operation, attempt)``."""
        with translate_application_errors():
            output = self._pods.execute(GetMaintenanceJobPodsUseCaseInput.from_primitives(request))
        return activity_payload(output)
