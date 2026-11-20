"""Define the TableMaintenanceWorkflow."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, FailureError, is_cancelled_exception

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    DEFAULT_START_SIZE,
    TABLE_MAINTENANCE_WORKFLOW,
    MaintenanceAttemptEnding,
    MaintenanceNextStep,
    OperationResultSignal,
    RaisePrioritySignal,
    TableMaintenanceActivity,
    TableMaintenanceSignal,
    TableMaintenanceWorkflowInput,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TableReconciliationSignal,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows.table_maintenance_attempt_policy import (
    TableMaintenanceAttemptPolicy,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

_ACTIVITY_TIMEOUT = timedelta(minutes=2)
_ACTIVITY_RETRY = RetryPolicy(maximum_attempts=5, initial_interval=timedelta(seconds=2), backoff_coefficient=2.0)
FAST_POLL_INTERVAL = timedelta(seconds=30)
FAST_POLL_WINDOW = timedelta(minutes=10)
SLOW_POLL_INTERVAL = timedelta(minutes=5)
QUEUED_POLL_INTERVAL = timedelta(minutes=10)
_CALLBACK_GRACE = timedelta(seconds=120)
_TIMED_OUT = "spark job timed out"
_MISSING = "spark job missing"
_QUEUE_TIMED_OUT = "spark job waited in the queue longer than the queue wait limit"
_NOT_REPLACED = "queued job could not be replaced"
_FENCE_PATCH = "fence-timed-out-attempt"
_FENCE_MISSING_PATCH = "fence-missing-job"
_FENCE_CANCELLED_PATCH = "fence-cancelled-attempt"
_CANCELLED = "cancelled"
_DECISION_PATCH = "classify-attempt-failure"
_PLANNED_POLICY_KEYS = ("policy_id", "policy_name", "policy_version", "policy_target")


@workflow.defn(name=TABLE_MAINTENANCE_WORKFLOW)
class TableMaintenanceWorkflow:
    """Run the planned operations of one maintenance run, in order, on Spark.

    A table runs one of these at a time, under the table's workflow id (see
    ``table_maintenance_workflow_id``). Each operation gets up to ``max_attempts`` attempts (input, 3 by
    default). An attempt is submitted straight to Spark, whose scheduler queues it, and ends with the job's
    ``operation_result`` callback for that exact run and attempt (a late result of an earlier run of the
    table, sent to the same workflow id, is ignored), with what polling the
    job's state reveals, or with a timeout. An attempt is queued from its submit until a status
    poll reports when its Spark driver started; that start, clamped between the submit and the
    poll, is recorded (``record_maintenance_attempt_running``; a failed record is logged) and
    starts the attempt's deadline, ``attempt_deadline_seconds`` (input, 6 h by default), so time
    spent waiting in the queue does not count toward it. An attempt still queued
    ``queue_wait_limit_seconds`` (input, 24 h by default) after its submit is fenced and ends
    ``queue_timed_out``. Polling runs every 30 s for the first 10 minutes of an attempt's queue
    wait and again for the first 10 minutes after its driver starts, then every 10 minutes while
    it is queued and every 5 minutes once it runs, which bounds the history. A timed-out attempt is
    fenced before the next one is submitted: its Spark job is deleted and its pods are
    polled until none is live (see
    ``TableMaintenanceFencingPolicy``); pods still live after the confirm bound fail
    the operation without a further attempt, and the next operation waits until they are
    gone. An attempt whose job went missing is fenced the same way, since its
    pods can outlive the SparkApplication. Histories from before fencing replay
    unfenced (patches ``fence-timed-out-attempt`` and ``fence-missing-job``). A
    cancellation (a manual cancel, or the reconciliation giving the run up) fences
    the attempt it interrupts the same way, without a bound and even if another
    cancel arrives meanwhile, before the run reports (patch
    ``fence-cancelled-attempt``). The first attempt runs at the plan's start size (S when the plan
    names none). Recording a failed attempt names how it ended and returns what follows it: an
    out-of-memory failure is retried at the next size, other failures at the same size, and a
    failure that needs a person, is not retried or may still be running ends the operation at once
    (patch ``classify-attempt-failure``; a record reply without a decision, as before failure
    classes, retries at the same size). Every record names the policy the run was planned under,
    by its id and its name then, from the plan, so a needs-attention mark is set under it and keeps
    the name for display; this changes only the record
    activity's input, not the workflow's commands, so it needs no patch. A plan from before policies
    had ids carries no ``policy_id``; its records then leave the policy to the recorder, which marks
    under the policy applying when it records. Every attempt submits the operation's ``filters``, also
    after running out of memory. A failed operation
    never fails the run: the next operation still runs. At the end, also after a
    cancellation, the Spark job of every started attempt is deleted and the parent
    reconciliation workflow is told the run finished and how many results could not be
    recorded.

    A ``raise_priority`` signal (a manual run asked for while this one runs) raises the run's
    priority, only upward, through ``raise_maintenance_run_priority``; a failed raise is logged and
    dropped. Raises are applied before every submit, so a later operation is submitted at the new
    priority, and as soon as they arrive while an attempt is awaited. An attempt that is running keeps
    going; one still queued is replaced: a status read that finds its driver started makes it running
    instead, otherwise its job is deleted, polled every 30 s until it reads ``NOT_FOUND`` and has no
    live pods, and submitted again under the same attempt number, keeping its submit time and queue
    deadline. A job not gone within the fencing confirm bound fails the attempt like an unconfirmed
    fence (ended ``missing``, possibly still running), and the operation waits until it is gone.
    """

    @workflow.init
    def __init__(self, input: TableMaintenanceWorkflowInput) -> None:  # noqa: A002
        """Prepare the result mailbox and the attempt log."""
        self._run_id = input.run_id
        self._policy = TableMaintenanceAttemptPolicy(
            max_attempts=input.max_attempts,
            attempt_deadline=timedelta(seconds=input.attempt_deadline_seconds),
            queue_wait_limit=timedelta(seconds=input.queue_wait_limit_seconds),
        )
        self._planned_policy = {key: input.plan.get(key) for key in _PLANNED_POLICY_KEYS}
        self._results: dict[tuple[str, int], OperationResultSignal] = {}
        self._started_attempts: list[tuple[str, int]] = []
        self._settled_attempts: set[tuple[str, int]] = set()
        self._record_failures = 0
        self._priority: str = input.plan.get("priority", "P3")
        self._raise_requests: list[RaisePrioritySignal] = []

    @workflow.run
    async def run(self, input: TableMaintenanceWorkflowInput) -> None:  # noqa: A002
        """Create the run, run each operation, then clean up and notify the parent."""
        operations: list[dict[str, Any]] = list(input.plan["operations"])
        try:
            await self._activity(
                TableMaintenanceActivity.CREATE_MAINTENANCE_RUN,
                {
                    "run_id": input.run_id,
                    "table_uuid": input.table_uuid,
                    "execution_ref": workflow.info().workflow_id,
                    "trigger": input.trigger,
                    "operations": [op["operation"] for op in operations],
                    "priority": input.plan.get("priority", "P3"),
                    "now": _now(),
                },
            )
            for operation in operations:
                await self._run_operation(operation)
        finally:
            await self._finish(input.parent_workflow_id)

    @workflow.signal(name=TableMaintenanceSignal.OPERATION_RESULT)
    def operation_result(self, result: OperationResultSignal) -> None:
        """Store a Spark job result under its operation and attempt."""
        if result.run_id != self._run_id:
            workflow.logger.warning("ignoring result for other run %s", result.run_id)
            return
        self._results.setdefault((result.operation, result.attempt), result)

    @workflow.signal(name=TableMaintenanceSignal.RAISE_PRIORITY)
    def raise_priority(self, request: RaisePrioritySignal) -> None:
        """Keep a priority raise until the workflow applies it."""
        self._raise_requests.append(request)

    async def _run_operation(self, operation: dict[str, Any]) -> None:
        size: str = operation.get("start_size") or DEFAULT_START_SIZE
        for attempt in range(1, self._policy.max_attempts + 1):
            outcome = await self._run_attempt(operation, attempt, size)
            if (outcome.operation, outcome.attempt) in self._settled_attempts:
                return
            decision = await self._record(outcome) or {}
            if outcome.succeeded:
                return
            step = decision.get("next_step")
            if step not in (None, MaintenanceNextStep.RETRY_SAME) and workflow.patched(_DECISION_PATCH):
                if step != MaintenanceNextStep.RETRY_LARGER:
                    return
                size = decision.get("next_size") or size
            if attempt < self._policy.max_attempts:
                await workflow.sleep(self._policy.backoff_after(attempt))

    async def _run_attempt(self, operation: dict[str, Any], attempt: int, size: str) -> OperationResultSignal:
        name = operation["operation"]
        try:
            return await self._attempt_outcome(operation, attempt, size)
        except asyncio.CancelledError:
            if (name, attempt) not in self._settled_attempts:
                await self._record(self._failure(name, attempt, _CANCELLED, MaintenanceAttemptEnding.CANCELLED))
            if (name, attempt) in self._started_attempts and workflow.patched(_FENCE_CANCELLED_PATCH):
                await _to_the_end(
                    self._fence(
                        name,
                        attempt,
                        _CANCELLED,
                        MaintenanceAttemptEnding.CANCELLED,
                        since="the cancel",
                        bounded=False,
                    )
                )
            raise

    async def _attempt_outcome(self, operation: dict[str, Any], attempt: int, size: str) -> OperationResultSignal:
        name = operation["operation"]
        self._started_attempts.append((name, attempt))
        try:
            job_name = await self._submit(operation, attempt, size)
        except ActivityError as error:
            _raise_if_cancelled(error)
            return self._submit_failed(name, attempt, error)
        return await self._await_outcome(operation, attempt, size, job_name)

    async def _submit(self, operation: dict[str, Any], attempt: int, size: str) -> str:
        """Apply the raises that arrived, then submit the attempt's job and return its name."""
        await self._apply_raises()
        submitted = await self._activity(
            TableMaintenanceActivity.SUBMIT_MAINTENANCE_OPERATION,
            {
                "run_id": self._run_id,
                "operation": operation["operation"],
                "attempt": attempt,
                "filters": operation["filters"],
                "procedure_args": operation["procedure_args"],
                "size": size,
                "now": _now(),
            },
        )
        return submitted["job_name"]

    async def _await_outcome(
        self, operation: dict[str, Any], attempt: int, size: str, job_name: str
    ) -> OperationResultSignal:
        """Wait for the attempt to end: queued until its driver starts, then bounded by its deadline from that start.

        A raise that arrives meanwhile is applied at once; a queued attempt it raised is replaced
        (see ``_requeue``), keeping its submit time, its queue deadline and its next poll.
        """
        name = operation["operation"]
        key = (name, attempt)
        submitted_at = workflow.now()
        running_since: datetime | None = None
        deadline = submitted_at + self._policy.queue_wait_limit
        completed_since: datetime | None = None
        poll_at: datetime | None = None
        while True:
            if key in self._results:
                return self._results[key]
            now = workflow.now()
            if now >= deadline:
                return await self._past_deadline(name, attempt, running=running_since is not None)
            if poll_at is None:
                in_fast_window = now - (running_since or submitted_at) < FAST_POLL_WINDOW
                poll_at = now + _poll_interval(in_fast_window=in_fast_window, running=running_since is not None)
            wait = min(poll_at, deadline) - now
            if wait > timedelta(0):
                try:
                    await workflow.wait_condition(
                        lambda: key in self._results or bool(self._raise_requests), timeout=wait
                    )
                except TimeoutError:
                    pass
            if key in self._results:
                return self._results[key]
            if self._raise_requests:
                started, replaced = await self._raise_attempt(operation, attempt, size, queued=running_since is None)
                if replaced is not None:
                    return replaced
                if started is not None:
                    running_since = await self._started_running(name, attempt, started, submitted_at)
                    deadline = running_since + self._policy.attempt_deadline
                    poll_at = None
                continue
            if workflow.now() >= deadline or workflow.now() < poll_at:
                continue
            poll_at = None
            status = await self._job_status(name, attempt)
            if status is None:
                continue
            if running_since is None and status.get("driver_started_at"):
                running_since = await self._started_running(name, attempt, status["driver_started_at"], submitted_at)
                deadline = running_since + self._policy.attempt_deadline
            if status["state"] != "COMPLETED":
                completed_since = None
            else:
                completed_since = completed_since or workflow.now()
            ended = await self._ended_by_status(name, attempt, job_name, status, completed_since)
            if ended is not None:
                return ended

    async def _ended_by_status(
        self, name: str, attempt: int, job_name: str, status: dict[str, Any], completed_since: datetime | None
    ) -> OperationResultSignal | None:
        """Return how the job's status ends the attempt, or None while it goes on.

        A failed job fails it, a missing one is fenced, and a job completed for the callback grace
        without its callback succeeds.
        """
        state = status["state"]
        if state == "FAILED":
            return self._failure(
                name, attempt, status["error"] or "spark job failed", MaintenanceAttemptEnding.JOB_FAILED
            )
        if state == "NOT_FOUND":
            return await self._missing(name, attempt)
        if completed_since is None or workflow.now() - completed_since < _CALLBACK_GRACE:
            return None
        workflow.logger.warning("%s completed without callback; recording success", job_name)
        return OperationResultSignal(
            run_id=self._run_id,
            operation=name,
            attempt=attempt,
            succeeded=True,
            metrics={"completed_without_callback": 1},
            error=None,
        )

    async def _apply_raises(self) -> bool:
        """Apply the raises that arrived, in order, and tell whether any raised the run.

        Each raise is recorded on the run, which keeps the higher priority; a raise that fails to
        record is logged and dropped.
        """
        raised = False
        while self._raise_requests:
            request = self._raise_requests.pop(0)
            try:
                reply = await self._activity(
                    TableMaintenanceActivity.RAISE_MAINTENANCE_RUN_PRIORITY,
                    {"run_id": self._run_id, "priority": request.priority, "now": _now()},
                )
            except ActivityError as error:
                _raise_if_cancelled(error)
                workflow.logger.warning("raising the priority of run %s failed: %s", self._run_id, error)
                continue
            self._priority = reply["priority"]
            raised = raised or bool(reply["raised"])
        return raised

    async def _raise_attempt(
        self, operation: dict[str, Any], attempt: int, size: str, *, queued: bool
    ) -> tuple[str | None, OperationResultSignal | None]:
        """Apply the raises that arrived and replace the attempt if it is ``queued`` and the run was raised.

        Returns what ``_requeue`` returns, or ``(None, None)`` when nothing is replaced.
        """
        if not await self._apply_raises() or not queued:
            return None, None
        return await self._requeue(operation, attempt, size)

    async def _requeue(
        self, operation: dict[str, Any], attempt: int, size: str
    ) -> tuple[str | None, OperationResultSignal | None]:
        """Replace a queued attempt's job so it is queued again at the raised priority.

        Returns ``(driver_started_at, None)`` when a status read finds the driver already started, so
        the attempt is running and is left alone; ``(None, failure)`` when the old job was not gone within
        the fencing confirm bound, or the new submit failed; ``(None, None)`` once the attempt is
        queued again (or a status read failed, so nothing was replaced). The job is deleted, polled
        every fencing poll until it reads ``NOT_FOUND`` and has no live pods, then submitted again
        under the same attempt number. A job still there at the bound is recorded as an unconfirmed
        fence is, and polled slowly until gone.
        """
        name = operation["operation"]
        status = await self._job_status(name, attempt)
        if status is None:
            workflow.logger.warning("not requeueing %s attempt %s: its status is unknown", name, attempt)
            return None, None
        if status.get("driver_started_at"):
            return status["driver_started_at"], None
        minutes = int(self._policy.fencing.confirm_bound.total_seconds() // 60)
        unconfirmed = await self._await_gone(
            name,
            attempt,
            MaintenanceAttemptEnding.MISSING,
            job_gone=True,
            unconfirmed_error=lambda still: f"{_NOT_REPLACED}: {still} {minutes} minutes after the priority raise",
        )
        if unconfirmed is not None:
            return None, unconfirmed
        try:
            await self._submit(operation, attempt, size)
        except ActivityError as error:
            _raise_if_cancelled(error)
            return None, self._submit_failed(name, attempt, error)
        return None, None

    async def _started_running(
        self, name: str, attempt: int, driver_started_at: str, submitted_at: datetime
    ) -> datetime:
        """Return when the attempt started running and record it; a failed record is logged and changes nothing.

        The driver's start is clamped into ``[submitted_at, now]``, so a pod clock
        ahead of or behind the workflow's never moves the deadline before the
        submit or into the future.
        """
        started = datetime.fromisoformat(driver_started_at)
        if started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
        now = workflow.now()
        running_since = min(max(started, submitted_at), now)
        try:
            await self._activity(
                TableMaintenanceActivity.RECORD_MAINTENANCE_ATTEMPT_RUNNING,
                {
                    "run_id": self._run_id,
                    "operation": name,
                    "attempt": attempt,
                    "started_running_at": running_since.isoformat(),
                    "now": now.isoformat(),
                },
            )
        except ActivityError as error:
            _raise_if_cancelled(error)
            workflow.logger.warning("recording %s attempt %s running failed: %s", name, attempt, error)
        return running_since

    async def _past_deadline(self, name: str, attempt: int, *, running: bool) -> OperationResultSignal:
        """End an attempt at its deadline: timed out once running, queue timed out while still queued."""
        if not running:
            return await self._queue_timed_out(name, attempt)
        return await self._timed_out(name, attempt)

    async def _queue_timed_out(self, name: str, attempt: int) -> OperationResultSignal:
        """Fence an attempt whose driver never started within the queue wait limit."""
        return await self._fence(
            name, attempt, _QUEUE_TIMED_OUT, MaintenanceAttemptEnding.QUEUE_TIMED_OUT, since="the queue wait limit"
        )

    async def _timed_out(self, name: str, attempt: int) -> OperationResultSignal:
        """Fence the timed-out attempt; a history from before fencing replays its immediate failure."""
        if workflow.patched(_FENCE_PATCH):
            return await self._fence(name, attempt, _TIMED_OUT, MaintenanceAttemptEnding.TIMED_OUT, since="the timeout")
        return self._failure(name, attempt, _TIMED_OUT, MaintenanceAttemptEnding.TIMED_OUT)

    async def _missing(self, name: str, attempt: int) -> OperationResultSignal:
        """Fence an attempt whose job went missing, as its pods may outlive it; older histories fail it at once."""
        if workflow.patched(_FENCE_MISSING_PATCH):
            return await self._fence(
                name, attempt, _MISSING, MaintenanceAttemptEnding.MISSING, since="the job went missing"
            )
        return self._failure(name, attempt, _MISSING, MaintenanceAttemptEnding.MISSING)

    async def _fence(  # noqa: PLR0913
        self,
        name: str,
        attempt: int,
        reason: str,
        ending: MaintenanceAttemptEnding,
        *,
        since: str,
        bounded: bool = True,
    ) -> OperationResultSignal:
        """Delete an ended attempt's job and wait until its pods are gone; nothing else is submitted meanwhile.

        ``reason`` is why the attempt ended (it timed out, waited in the queue
        too long, or its job went missing), ``ending`` names that ending for the record, and ``since``
        names that moment in the error of an unconfirmed fence. An unbounded
        fence (after a cancel) records nothing and waits for the pods however
        long they take, polling slowly once past the bound so its history stays
        small.

        Each poll tries the delete again until one has succeeded, and only
        then reads the pods. A result that arrives now is
        ignored: the attempt has ended, and the next reconcile reads the table
        to see what it did. Pods gone within the confirm bound (counted from
        when the attempt ended) fail the attempt with ``reason``, so the caller
        retries. Pods still live at the bound, or a job that could not
        be deleted by then, fail the operation for good: the failure is
        recorded at once, then polling goes on, slower, until the pods are
        gone, and only then does the caller go on.
        """
        minutes = int(self._policy.fencing.confirm_bound.total_seconds() // 60)
        unconfirmed = await self._await_gone(
            name,
            attempt,
            ending,
            bounded=bounded,
            unconfirmed_error=lambda still: f"{reason}; {still} {minutes} minutes after {since}",
        )
        return unconfirmed or self._failure(name, attempt, reason, ending)

    async def _await_gone(  # noqa: PLR0913
        self,
        name: str,
        attempt: int,
        ending: MaintenanceAttemptEnding,
        *,
        unconfirmed_error: Callable[[str], str],
        bounded: bool = True,
        job_gone: bool = False,
    ) -> OperationResultSignal | None:
        """Delete an attempt's job and poll until its pods (and, with ``job_gone``, the job) are gone.

        Returns None when they were gone within the confirm bound. Otherwise, when ``bounded``, the
        attempt is recorded at the bound as failed with ``unconfirmed_error`` of what was still there
        and possibly still running, polling goes on slower until they are gone, and that failure is
        returned.
        """
        fencing = self._policy.fencing
        key = (name, attempt)
        confirm_by = workflow.now() + fencing.confirm_bound
        deleted = False
        outcome: OperationResultSignal | None = None
        while True:
            deleted = deleted or await self._delete_job(name, attempt)
            job_absent = deleted and (not job_gone or await self._job_absent(name, attempt))
            if job_absent and await self._pods_gone(name, attempt):
                return outcome
            if bounded and key not in self._settled_attempts and workflow.now() >= confirm_by:
                if not deleted:
                    still = "its job could still not be deleted"
                elif not job_absent:
                    still = "its job was still there"
                else:
                    still = "its pods were still running"
                outcome = self._failure(name, attempt, unconfirmed_error(still), ending, still_running=True)
                await self._record(outcome)
                self._settled_attempts.add(key)
            slow = key in self._settled_attempts or workflow.now() >= confirm_by
            await workflow.sleep(fencing.slow_poll_interval if slow else fencing.poll_interval)

    async def _job_absent(self, name: str, attempt: int) -> bool:
        """Tell whether the attempt's job reads ``NOT_FOUND``; an unknown status counts as present."""
        status = await self._job_status(name, attempt)
        return status is not None and status["state"] == "NOT_FOUND"

    async def _delete_job(self, name: str, attempt: int) -> bool:
        try:
            await self._activity(
                TableMaintenanceActivity.DELETE_MAINTENANCE_JOB,
                {"run_id": self._run_id, "operation": name, "attempt": attempt},
            )
        except ActivityError as error:
            _raise_if_cancelled(error)
            workflow.logger.warning("deleting the job of %s attempt %s failed: %s", name, attempt, error)
            return False
        return True

    async def _pods_gone(self, name: str, attempt: int) -> bool:
        try:
            pods = await self._activity(
                TableMaintenanceActivity.GET_MAINTENANCE_JOB_PODS,
                {"run_id": self._run_id, "operation": name, "attempt": attempt},
            )
        except ActivityError as error:
            _raise_if_cancelled(error)
            workflow.logger.warning("pods of %s attempt %s unknown: %s", name, attempt, error)
            return False
        return not pods["live_pods"]

    async def _job_status(self, name: str, attempt: int) -> dict[str, Any] | None:
        try:
            return await self._activity(
                TableMaintenanceActivity.GET_MAINTENANCE_JOB_STATUS,
                {"run_id": self._run_id, "operation": name, "attempt": attempt},
            )
        except ActivityError as error:
            _raise_if_cancelled(error)
            workflow.logger.warning("status of %s attempt %s unknown: %s", name, attempt, error)
            return None

    async def _record(self, outcome: OperationResultSignal) -> dict[str, Any] | None:
        """Record the attempt and return the record's reply, with what follows it; None when it was not recorded."""
        try:
            return await self._activity(
                TableMaintenanceActivity.RECORD_MAINTENANCE_OPERATION_RESULT,
                {
                    "run_id": outcome.run_id,
                    "operation": outcome.operation,
                    "attempt": outcome.attempt,
                    "succeeded": outcome.succeeded,
                    "metrics": outcome.metrics,
                    "error": outcome.error,
                    "ended_by": outcome.ended_by,
                    "still_running": outcome.still_running,
                    "max_attempts": self._policy.max_attempts,
                    **self._planned_policy,
                    "now": _now(),
                },
            )
        except ActivityError as error:
            _raise_if_cancelled(error)
            self._record_failures += 1
            workflow.logger.error(
                "recording %s attempt %s failed: %s",
                outcome.operation,
                outcome.attempt,
                error,
            )
            return None

    async def _finish(self, parent_workflow_id: str) -> None:
        for name, attempt in self._started_attempts:
            try:
                await self._activity(
                    TableMaintenanceActivity.DELETE_MAINTENANCE_JOB,
                    {"run_id": self._run_id, "operation": name, "attempt": attempt},
                )
            except ActivityError as error:
                workflow.logger.warning("deleting the job of %s attempt %s failed: %s", name, attempt, error)
        try:
            await self._activity(
                TableMaintenanceActivity.SIGNAL_PARENT,
                {
                    "workflow_id": parent_workflow_id,
                    "signal": TableReconciliationSignal.MAINTENANCE_FINISHED,
                    "arg": {
                        "run_id": self._run_id,
                        "record_failures": self._record_failures,
                    },
                },
            )
        except ActivityError as error:
            workflow.logger.warning("signalling the parent failed: %s", error)
        await workflow.wait_condition(workflow.all_handlers_finished)

    def _submit_failed(self, name: str, attempt: int, error: ActivityError) -> OperationResultSignal:
        return self._failure(name, attempt, f"submit failed: {_message(error)}", MaintenanceAttemptEnding.SUBMIT_FAILED)

    def _failure(
        self,
        name: str,
        attempt: int,
        error: str,
        ending: MaintenanceAttemptEnding,
        *,
        still_running: bool = False,
    ) -> OperationResultSignal:
        return OperationResultSignal(
            run_id=self._run_id,
            operation=name,
            attempt=attempt,
            succeeded=False,
            metrics={},
            error=error,
            ended_by=ending,
            still_running=still_running,
        )

    async def _activity(self, name: str, request: dict[str, Any]) -> Any:  # noqa: ANN401
        return await workflow.execute_activity(
            name,
            request,
            start_to_close_timeout=_ACTIVITY_TIMEOUT,
            retry_policy=_ACTIVITY_RETRY,
        )


def _poll_interval(*, in_fast_window: bool, running: bool) -> timedelta:
    """Return the wait before the next status poll: fast first, then slow once running, slower while queued."""
    if in_fast_window:
        return FAST_POLL_INTERVAL
    return SLOW_POLL_INTERVAL if running else QUEUED_POLL_INTERVAL


def _now() -> str:
    return workflow.now().isoformat()


def _message(error: ActivityError) -> str:
    cause = error.cause
    return cause.message if isinstance(cause, FailureError) else error.message


async def _to_the_end[T](work: Coroutine[Any, Any, T]) -> T:
    """Run ``work`` to its end even when the workflow is cancelled again while it runs."""
    task = asyncio.ensure_future(work)
    while True:
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            if task.cancelled():
                raise


def _raise_if_cancelled(error: ActivityError) -> None:
    """Turn an activity cancelled by a workflow cancellation back into the cancel."""
    if is_cancelled_exception(error):
        raise asyncio.CancelledError from error
