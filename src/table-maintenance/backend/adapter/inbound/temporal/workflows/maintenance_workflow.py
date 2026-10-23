"""Define the MaintenanceWorkflow."""

from __future__ import annotations

import asyncio
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
ATTEMPT_DEADLINE_SECONDS = 21600
FAST_POLL_INTERVAL = timedelta(seconds=30)
FAST_POLL_WINDOW = timedelta(minutes=10)
SLOW_POLL_INTERVAL = timedelta(minutes=5)
_CALLBACK_GRACE = timedelta(seconds=120)
_ACQUIRE_RESEND_INTERVAL = timedelta(minutes=5)


@workflow.defn(name=MAINTENANCE_WORKFLOW)
class MaintenanceWorkflow:
    """Run the planned operations of one maintenance run, in order, on Spark.

    Each operation gets up to three attempts. An attempt holds one capacity slot
    from the limiter while its Spark job runs, and ends with the job's
    ``operation_result`` callback for that exact attempt, with what polling the
    job's state reveals, or with a timeout ``ATTEMPT_DEADLINE_SECONDS`` after the
    submit. Polling runs every 30 s for the first 10 minutes of an attempt and
    every 5 minutes after that, which bounds the history. A failed operation
    never fails the run: the next operation still runs. At the end, also after a
    cancellation, the Spark job of every started attempt is deleted and the parent
    reconcile workflow is told the run finished and how many results could not be
    recorded.
    """

    @workflow.init
    def __init__(self, input: MaintenanceWorkflowInput) -> None:  # noqa: A002
        """Prepare the result and grant mailboxes and the attempt log."""
        self._run_id = input.run_id
        self._results: dict[tuple[str, int], OperationResultSignal] = {}
        self._granted: set[str] = set()
        self._current_request: str | None = None
        self._started_attempts: list[tuple[str, int]] = []
        self._record_failures = 0

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
    async def capacity_granted(self, request_id: str) -> None:
        """Take the grant of the awaited request; hand any other grant straight back."""
        if request_id == self._current_request:
            self._granted.add(request_id)
            return
        workflow.logger.warning("releasing unexpected grant %s", request_id)
        await self._release(request_id)

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
        self._current_request = request_id
        try:
            return await self._attempt_outcome(operation, attempt, request_id)
        except asyncio.CancelledError:
            await self._record(self._failure(name, attempt, "cancelled"))
            raise
        finally:
            self._current_request = None
            await self._release(request_id)

    async def _attempt_outcome(
        self, operation: dict[str, Any], attempt: int, request_id: str
    ) -> OperationResultSignal:
        name = operation["operation"]
        try:
            await self._acquire(request_id)
        except ActivityError as error:
            return self._failure(
                name, attempt, f"capacity acquire failed: {_message(error)}"
            )
        self._started_attempts.append((name, attempt))
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
        return await self._await_outcome(name, attempt, submitted["app_name"])

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
        submitted_at = workflow.now()
        deadline = submitted_at + timedelta(seconds=ATTEMPT_DEADLINE_SECONDS)
        completed_since: datetime | None = None
        while True:
            now = workflow.now()
            if now >= deadline:
                return self._failure(name, attempt, "spark job timed out")
            in_fast_window = now - submitted_at < FAST_POLL_WINDOW
            interval = FAST_POLL_INTERVAL if in_fast_window else SLOW_POLL_INTERVAL
            try:
                await workflow.wait_condition(
                    lambda: key in self._results, timeout=min(interval, deadline - now)
                )
                return self._results[key]
            except TimeoutError:
                pass
            if workflow.now() >= deadline:
                continue
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
            if state != "COMPLETED":
                completed_since = None
                continue
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
                    metrics={"completed_without_callback": 1},
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
            self._record_failures += 1
            workflow.logger.error(
                "recording %s attempt %s failed: %s",
                outcome.operation,
                outcome.attempt,
                error,
            )

    async def _finish(self, parent_workflow_id: str) -> None:
        for name, attempt in self._started_attempts:
            try:
                await self._activity(
                    DELETE_MAINTENANCE_JOB,
                    {"run_id": self._run_id, "operation": name, "attempt": attempt},
                )
            except ActivityError as error:
                workflow.logger.warning(
                    "deleting the job of %s attempt %s failed: %s", name, attempt, error
                )
        try:
            await self._activity(
                SIGNAL_PARENT,
                {
                    "workflow_id": parent_workflow_id,
                    "signal": SIGNAL_MAINTENANCE_FINISHED,
                    "arg": {
                        "run_id": self._run_id,
                        "record_failures": self._record_failures,
                    },
                },
            )
        except ActivityError as error:
            workflow.logger.warning("signalling the parent failed: %s", error)
        await workflow.wait_condition(workflow.all_handlers_finished)

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
