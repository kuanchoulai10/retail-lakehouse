"""Define the TableMaintenanceActivities Temporal activities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from temporalio import activity
from temporalio.client import RPCError
from temporalio.service import RPCStatusCode

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    TableMaintenanceActivity,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities.activity_payload import (
    activity_payload,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities.translate_application_errors import (
    translate_application_errors,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    CreateTableMaintenanceRunUseCaseInput,
    DeleteMaintenanceJobUseCaseInput,
    GetMaintenanceJobPodsUseCaseInput,
    GetMaintenanceJobStatusUseCaseInput,
    RaiseTableMaintenanceRunPriorityUseCaseInput,
    RecordMaintenanceAttemptRunningUseCaseInput,
    RecordTableMaintenanceOperationResultUseCaseInput,
    SkipTableMaintenanceRunUseCaseInput,
    SubmitMaintenanceOperationUseCaseInput,
)

if TYPE_CHECKING:
    from temporalio.client import Client

    from context.table_maintenance.application.port.inbound.table_maintenance_run import (
        CreateTableMaintenanceRunUseCase,
        DeleteMaintenanceJobUseCase,
        GetMaintenanceJobPodsUseCase,
        GetMaintenanceJobStatusUseCase,
        RaiseTableMaintenanceRunPriorityUseCase,
        RecordMaintenanceAttemptRunningUseCase,
        RecordTableMaintenanceOperationResultUseCase,
        SkipTableMaintenanceRunUseCase,
        SubmitMaintenanceOperationUseCase,
    )


class TableMaintenanceActivities:
    """Run a table maintenance workflow: its runs, their Spark jobs and its parent.

    Each method wraps exactly one use case, except the signal wiring, which talks to
    the Temporal client. Inputs and outputs are primitive dicts.
    """

    def __init__(
        self,
        *,
        create_run: CreateTableMaintenanceRunUseCase,
        record_result: RecordTableMaintenanceOperationResultUseCase,
        submit: SubmitMaintenanceOperationUseCase,
        status: GetMaintenanceJobStatusUseCase,
        delete: DeleteMaintenanceJobUseCase,
        pods: GetMaintenanceJobPodsUseCase,
        record_running: RecordMaintenanceAttemptRunningUseCase,
        raise_priority: RaiseTableMaintenanceRunPriorityUseCase,
        skip: SkipTableMaintenanceRunUseCase,
        client: Client,
        callback_base_url: str,
    ) -> None:
        """Bind the use cases, the client and the base URL Spark jobs call back to."""
        self._create_run = create_run
        self._record_result = record_result
        self._submit = submit
        self._status = status
        self._delete = delete
        self._pods = pods
        self._record_running = record_running
        self._raise_priority = raise_priority
        self._skip = skip
        self._client = client
        self._callback_base_url = callback_base_url

    @activity.defn(name=TableMaintenanceActivity.CREATE_MAINTENANCE_RUN)
    def create_table_maintenance_run(self, request: dict[str, Any]) -> dict[str, Any]:
        """Create the pending run of one planned operation, with its filters and procedure arguments."""
        with translate_application_errors():
            output = self._create_run.execute(CreateTableMaintenanceRunUseCaseInput.from_primitives(request))
        return activity_payload(output)

    @activity.defn(name=TableMaintenanceActivity.RECORD_MAINTENANCE_OPERATION_RESULT)
    def record_table_maintenance_operation_result(self, request: dict[str, Any]) -> dict[str, Any]:
        """Record the outcome of one operation attempt; an older request reads as a reported result."""
        with translate_application_errors():
            output = self._record_result.execute(
                RecordTableMaintenanceOperationResultUseCaseInput.from_primitives(request)
            )
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

    @activity.defn(name=TableMaintenanceActivity.RECORD_MAINTENANCE_ATTEMPT_RUNNING)
    def record_maintenance_attempt_running(self, request: dict[str, Any]) -> dict[str, Any]:
        """Record when the driver of one ``(run_id, operation, attempt)`` started running."""
        with translate_application_errors():
            output = self._record_running.execute(RecordMaintenanceAttemptRunningUseCaseInput.from_primitives(request))
        return activity_payload(output)

    @activity.defn(name=TableMaintenanceActivity.RAISE_MAINTENANCE_RUN_PRIORITY)
    def raise_table_maintenance_run_priority(self, request: dict[str, Any]) -> dict[str, Any]:
        """Raise the priority of a run in flight, only upward, and return its priority and whether it rose."""
        with translate_application_errors():
            output = self._raise_priority.execute(RaiseTableMaintenanceRunPriorityUseCaseInput.from_primitives(request))
        return activity_payload(output)

    @activity.defn(name=TableMaintenanceActivity.SKIP_MAINTENANCE_RUN)
    def skip_table_maintenance_run(self, request: dict[str, Any]) -> dict[str, Any]:
        """Skip a run that never started, saying why; a run no longer pending is left alone and reported not skipped."""
        with translate_application_errors():
            output = self._skip.execute(SkipTableMaintenanceRunUseCaseInput.from_primitives(request))
        return activity_payload(output)

    @activity.defn(name=TableMaintenanceActivity.SIGNAL_PARENT)
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
