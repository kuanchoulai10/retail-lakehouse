"""Define the MaintenanceWorkflow."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, FailureError

from adapter.temporal_contracts.activity_names import (
    CREATE_MAINTENANCE_RUN,
    DELETE_MAINTENANCE_JOB,
    GET_MAINTENANCE_JOB_STATUS,
    RECORD_MAINTENANCE_OPERATION_RESULT,
    SIGNAL_CAPACITY_ACQUIRE,
    SIGNAL_PARENT,
    SUBMIT_MAINTENANCE_OPERATION,
)
from adapter.temporal_contracts.capacity_release_signal import CapacityReleaseSignal
from adapter.temporal_contracts.maintenance_workflow_input import (
    MaintenanceWorkflowInput,
)
from adapter.temporal_contracts.operation_result_signal import OperationResultSignal
from adapter.temporal_contracts.workflow_names import MAINTENANCE_WORKFLOW
from application.domain.model.maintenance.workflow_ids import (
    CAPACITY_WORKFLOW_ID,
    SIGNAL_CAPACITY_GRANTED,
    SIGNAL_CAPACITY_RELEASE,
    SIGNAL_MAINTENANCE_FINISHED,
    SIGNAL_OPERATION_RESULT,
)

_ACTIVITY_TIMEOUT = timedelta(minutes=2)
_ACTIVITY_RETRY = RetryPolicy(
    maximum_attempts=5, initial_interval=timedelta(seconds=2), backoff_coefficient=2.0
)
_MAX_ATTEMPTS = 3
_BACKOFFS = (timedelta(seconds=60), timedelta(seconds=120))
_POLL_INTERVAL = timedelta(seconds=30)
_CALLBACK_GRACE = timedelta(seconds=120)
_ACQUIRE_RESEND_INTERVAL = timedelta(minutes=5)


@workflow.defn(name=MAINTENANCE_WORKFLOW)
class MaintenanceWorkflow:
    """Run the planned operations of one maintenance run, in order, on Spark.

    Each operation gets up to three attempts. An attempt holds one capacity slot
    from the limiter while its Spark job runs, and ends with the job's
    ``operation_result`` callback for that exact attempt or, failing that, with
    what polling the job's state reveals. A failed operation never fails the run:
    the next operation still runs. At the end every submitted job is deleted and
    the parent reconcile workflow is told the run finished.
    """

    @workflow.init
    def __init__(self, input: MaintenanceWorkflowInput) -> None:  # noqa: A002
        """Prepare the result and grant mailboxes."""
        self._run_id = input.run_id
        self._results: dict[tuple[str, int], OperationResultSignal] = {}
        self._granted: set[str] = set()
        self._app_names: list[str] = []

    @workflow.run
    async def run(self, input: MaintenanceWorkflowInput) -> None:  # noqa: A002
        """Create the run, run each operation, then clean up and notify the parent."""
        operations: list[dict[str, Any]] = list(input.plan["operations"])
        try:
            await self._activity(
                CREATE_MAINTENANCE_RUN,
                {
                    "run_id": input.run_id,
                    "table_uuid": input.table_uuid,
                    "trigger": input.trigger,
                    "operations": [op["operation"] for op in operations],
                    "now": _now(),
                },
            )
            for operation in operations:
                await self._run_operation(operation)
        finally:
            await self._finish(input.parent_workflow_id)

    @workflow.signal(name=SIGNAL_OPERATION_RESULT)
    def operation_result(self, result: OperationResultSignal) -> None:
        """Store a Spark job result under its operation and attempt."""
        if result.run_id != self._run_id:
            workflow.logger.warning("ignoring result for other run %s", result.run_id)
            return
        self._results.setdefault((result.operation, result.attempt), result)

    @workflow.signal(name=SIGNAL_CAPACITY_GRANTED)
    def capacity_granted(self, request_id: str) -> None:
        """Note that the limiter granted a capacity request."""
        self._granted.add(request_id)

    async def _run_operation(self, operation: dict[str, Any]) -> None:
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            outcome = await self._run_attempt(operation, attempt)
            await self._record(outcome)
            if outcome.succeeded:
                return
            if attempt < _MAX_ATTEMPTS:
                await workflow.sleep(_BACKOFFS[attempt - 1])

    async def _run_attempt(
        self, operation: dict[str, Any], attempt: int
    ) -> OperationResultSignal:
        name = operation["operation"]
        request_id = f"{self._run_id}-{name}-{attempt}"
        try:
            try:
                await self._acquire(request_id)
            except ActivityError as error:
                return self._failure(
                    name, attempt, f"capacity acquire failed: {_message(error)}"
                )
            try:
                submitted = await self._activity(
                    SUBMIT_MAINTENANCE_OPERATION,
                    {
                        "run_id": self._run_id,
                        "operation": name,
                        "attempt": attempt,
                        "filters": operation["filters"],
                        "procedure_args": operation["procedure_args"],
                        "now": _now(),
                    },
                )
            except ActivityError as error:
                return self._failure(name, attempt, f"submit failed: {_message(error)}")
            self._app_names.append(submitted["app_name"])
            return await self._await_outcome(name, attempt, submitted["app_name"])
        finally:
            await self._release(request_id)

    async def _acquire(self, request_id: str) -> None:
        request = {
            "request_id": request_id,
            "requester_workflow_id": workflow.info().workflow_id,
        }
        await self._activity(SIGNAL_CAPACITY_ACQUIRE, request)
        while True:
            try:
                await workflow.wait_condition(
                    lambda: request_id in self._granted,
                    timeout=_ACQUIRE_RESEND_INTERVAL,
                )
                return
            except TimeoutError:
                await self._activity(SIGNAL_CAPACITY_ACQUIRE, request)

    async def _release(self, request_id: str) -> None:
        handle = workflow.get_external_workflow_handle(CAPACITY_WORKFLOW_ID)
        try:
            await handle.signal(
                SIGNAL_CAPACITY_RELEASE, CapacityReleaseSignal(request_id)
            )
        except FailureError as error:
            workflow.logger.warning("release of %s failed: %s", request_id, error)

    async def _await_outcome(
        self, name: str, attempt: int, app_name: str
    ) -> OperationResultSignal:
        key = (name, attempt)
        completed_since: datetime | None = None
        while True:
            try:
                await workflow.wait_condition(
                    lambda: key in self._results, timeout=_POLL_INTERVAL
                )
                return self._results[key]
            except TimeoutError:
                pass
            status = await self._job_status(app_name)
            if status is None:
                continue
            state = status["state"]
            if state == "FAILED":
                return self._failure(
                    name, attempt, status["error"] or "spark job failed"
                )
            if state == "NOT_FOUND":
                return self._failure(name, attempt, "spark job missing")
            if state == "COMPLETED":
                completed_since = completed_since or workflow.now()
                if workflow.now() - completed_since >= _CALLBACK_GRACE:
                    workflow.logger.warning(
                        "%s completed without callback; recording success", app_name
                    )
                    return OperationResultSignal(
                        run_id=self._run_id,
                        operation=name,
                        attempt=attempt,
                        succeeded=True,
                        metrics={},
                        error=None,
                    )

    async def _job_status(self, app_name: str) -> dict[str, Any] | None:
        try:
            return await self._activity(
                GET_MAINTENANCE_JOB_STATUS, {"app_name": app_name}
            )
        except ActivityError as error:
            workflow.logger.warning("status of %s unknown: %s", app_name, error)
            return None

    async def _record(self, outcome: OperationResultSignal) -> None:
        try:
            await self._activity(
                RECORD_MAINTENANCE_OPERATION_RESULT,
                {
                    "run_id": outcome.run_id,
                    "operation": outcome.operation,
                    "attempt": outcome.attempt,
                    "succeeded": outcome.succeeded,
                    "metrics": outcome.metrics,
                    "error": outcome.error,
                    "now": _now(),
                },
            )
        except ActivityError as error:
            workflow.logger.error(
                "recording %s attempt %s failed: %s",
                outcome.operation,
                outcome.attempt,
                error,
            )

    async def _finish(self, parent_workflow_id: str) -> None:
        for app_name in self._app_names:
            try:
                await self._activity(DELETE_MAINTENANCE_JOB, {"app_name": app_name})
            except ActivityError as error:
                workflow.logger.warning("deleting %s failed: %s", app_name, error)
        try:
            await self._activity(
                SIGNAL_PARENT,
                {
                    "workflow_id": parent_workflow_id,
                    "signal": SIGNAL_MAINTENANCE_FINISHED,
                    "arg": self._run_id,
                },
            )
        except ActivityError as error:
            workflow.logger.warning("signalling the parent failed: %s", error)

    def _failure(self, name: str, attempt: int, error: str) -> OperationResultSignal:
        return OperationResultSignal(
            run_id=self._run_id,
            operation=name,
            attempt=attempt,
            succeeded=False,
            metrics={},
            error=error,
        )

    async def _activity(self, name: str, request: dict[str, Any]) -> Any:  # noqa: ANN401
        return await workflow.execute_activity(
            name,
            request,
            start_to_close_timeout=_ACTIVITY_TIMEOUT,
            retry_policy=_ACTIVITY_RETRY,
        )


def _now() -> str:
    return workflow.now().isoformat()


def _message(error: ActivityError) -> str:
    cause = error.cause
    return cause.message if isinstance(cause, FailureError) else error.message
