"""Define the TableMaintenanceWorkflow."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from temporalio import workflow
from temporalio.exceptions import ActivityError, FailureError, is_cancelled_exception

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
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
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows.table_maintenance_activity_policy import (
    TableMaintenanceActivityPolicy,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows.table_maintenance_attempt_policy import (
    TableMaintenanceAttemptPolicy,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

_ACTIVITIES = TableMaintenanceActivityPolicy()
FAST_POLL_INTERVAL = timedelta(seconds=30)
FAST_POLL_WINDOW = timedelta(minutes=10)
SLOW_POLL_INTERVAL = timedelta(minutes=5)
QUEUED_POLL_INTERVAL = timedelta(minutes=10)
SUBMITTING_POLL_INTERVAL = timedelta(seconds=5)
_CALLBACK_GRACE = timedelta(seconds=120)
_TIMED_OUT = "spark job timed out"
_MISSING = "spark job missing"
_QUEUE_TIMED_OUT = "spark job waited in the queue longer than the queue wait limit"
_NOT_REPLACED = "queued job could not be replaced"
_CANCELLED = "cancelled"
_STARTED_STATES = frozenset({"RUNNING", "COMPLETED"})
_PLANNED_POLICY_KEYS = ("policy_id", "policy_name", "policy_version", "policy_target")
_NOT_REACHED = "the table's maintenance stopped before this run started"
_PENDING = "pending"
_RETRY_WAITING = "retry_waiting"
_RETRYING_STEPS = frozenset({MaintenanceNextStep.RETRY_SAME, MaintenanceNextStep.RETRY_LARGER})


@workflow.defn(name=TABLE_MAINTENANCE_WORKFLOW)
class TableMaintenanceWorkflow:
    """Run the planned operations of one plan on Spark, each as its own maintenance run, one at a time.

    A table runs one of these at a time, under the table's workflow id (see
    ``table_maintenance_workflow_id``). The parent names one run id per planned operation
    (``run_ids``, in plan order), whose runs it created, pending, in one transaction before starting
    this workflow, so every run exists before anything is submitted. The workflow runs them in plan order: a
    run's first submit comes only after the previous run's last attempt was recorded and its Spark
    jobs are gone, so a table has one Spark job at a time and the executors kept for evidence are freed
    before the next job queues. Each job of the ended run is deleted and polled, as a fence polls,
    until it reads ``NOT_FOUND`` and has no live pods, however long that takes; nothing is recorded,
    since the run already ended.

    Each run gets up to ``max_attempts`` attempts (input, 3 by default). An attempt is submitted
    straight to Spark, whose scheduler queues it, and ends with the job's ``operation_result``
    callback for that exact run and attempt (a result naming any other run, such as a late result
    of an earlier execution sent to the same workflow id, or one naming another run of this plan,
    is ignored, and so is one for an attempt not submitted yet or whose run already ended), with
    what polling the
    job's state reveals, or with a timeout. An attempt is queued from its submit until a status
    poll reports when its Spark driver started; that start, clamped between the submit and the
    poll, is recorded (``record_maintenance_attempt_running``; a failed record is logged) and
    starts the attempt's deadline, ``attempt_deadline_seconds`` (input, 6 h by default), so time
    spent waiting in the queue does not count toward it. An attempt still queued
    ``queue_wait_limit_seconds`` (input, 24 h by default) after its submit is polled once more: a job
    read running or completed then (its driver start, unreadable, taken as that poll) is running, a
    failed or missing one ends as any poll would, and otherwise it is fenced and ends ``queue_timed_out``.
    Polling runs every 30 s for the first 10 minutes of an attempt's queue wait and again for the
    first 10 minutes after its driver starts, then every 10 minutes while it is queued and every 5
    minutes once it runs, which bounds the history. A timed-out attempt is
    fenced before the next one is submitted: its Spark job is deleted and its pods are
    polled until none is live (see
    ``TableMaintenanceFencingPolicy``); pods still live after the confirm bound fail
    the run without a further attempt, and the next run waits until they are
    gone. An attempt whose job went missing is fenced the same way, since its
    pods can outlive the SparkApplication. A
    cancellation (a manual cancel, or the reconciliation giving the run up) fences
    the attempt it interrupts the same way, without a bound and even if another
    cancel arrives meanwhile, before the run reports; recording that attempt cancels the run. A
    cancellation while a run waits out the backoff before its retry, with no attempt in flight,
    cancels that run itself (``cancel_maintenance_run``; a failed cancel is logged), and so does one
    that arrives while a failed attempt is recorded: that record runs to its end first, and a reply that
    retries is followed by the cancel of the run. So a run never stays waiting to retry. The first
    attempt runs at the plan's start size.
    Recording a failed attempt names how it ended and returns what follows it: an
    out-of-memory failure is retried at the next size, other failures at the same size, and a
    failure that needs a person, is not retried or may still be running ends the run at once; a
    record that failed, and so answers no decision, retries at the same size. Every record names the
    policy the run was planned under, by its id and its name then, from the plan, so a needs-attention
    mark is set under it and keeps the name for display. Every attempt runs with the job content its run was
    created with, also after running out of memory; the submit reads them from
    the run. A failed run, a failed submit included, never stops the workflow: the next run still
    runs. An attempt whose submit never saved it (a cancel, or a submit refused first, such as for a
    table not found) leaves its run pending, and recording it answers so: that counts no record
    failure, and a run whose submit was refused that way is skipped with the refusal (``submit
    failed: ...``) as its reason and submitted no more. At the end, also after a cancellation, the
    Spark job of every attempt not yet gone is deleted and waited for in the same way, even if another
    cancel arrives meanwhile, so the workflow never closes with a job still deleting. Then every run of
    the plan none of whose
    submits returned is skipped
    (``skip_maintenance_run``, which leaves a run no longer pending as it is), and the parent
    reconciliation workflow is told the runs finished and how many results could not be recorded.

    A ``raise_priority`` signal (a manual run asked for while this one runs) raises the priority of
    the current run and then of every run after it, only upward, through
    ``raise_maintenance_run_priority``; a failed raise is logged and dropped. Raises are applied before
    every submit, so a retry and a later run are submitted at the new priority, and as soon as they
    arrive while an attempt is awaited. Only the current run's reply decides whether its queued
    attempt is replaced. An attempt that is running keeps
    going; one still queued is polled at once, and only a job that reads ``PENDING`` without a driver
    start is replaced: its job is deleted, polled every 30 s until it reads ``NOT_FOUND`` and has no
    live pods, and submitted again under the same attempt number, keeping its submit time and queue
    deadline (a status that cannot be read leaves the replacement to the next poll); a result the
    deleted job sent meanwhile is dropped. A job not gone within the fencing confirm bound fails the
    attempt like an unconfirmed fence (ended ``missing``, possibly still running), and the run
    waits until it is gone. The parent is told, with the runs' end (``run_ids``), whether a raise was
    left unapplied (``unapplied_raise``: it arrived after the last attempt ended, or a record of it
    failed) and how many raises the workflow had received when it built that report
    (``raises_received``), so
    the parent can tell a raise that arrived later and still plan the manual run behind it.
    """

    @workflow.init
    def __init__(self, input: TableMaintenanceWorkflowInput) -> None:  # noqa: A002
        """Pair each planned operation with its run, and prepare the result mailbox and the attempt log."""
        self._operations: list[str] = [op["operation"] for op in input.plan["operations"]]
        self._run_ids = list(input.run_ids)
        self._run_of: dict[str, str] = dict(zip(self._operations, self._run_ids, strict=True))
        self._submitted: set[str] = set()
        self._skipped: set[str] = set()
        self._current: str | None = None
        self._policy = TableMaintenanceAttemptPolicy(
            max_attempts=input.max_attempts,
            attempt_deadline=timedelta(seconds=input.attempt_deadline_seconds),
            queue_wait_limit=timedelta(seconds=input.queue_wait_limit_seconds),
        )
        self._planned_policy = {key: input.plan[key] for key in _PLANNED_POLICY_KEYS}
        self._results: dict[tuple[str, int], OperationResultSignal] = {}
        self._last_submit_at: dict[str, datetime] = {}
        self._started_attempts: list[tuple[str, int]] = []
        self._settled_attempts: set[tuple[str, int]] = set()
        self._record_failures = 0
        self._raise_requests: list[RaisePrioritySignal] = []
        self._dropped_raise = False
        self._raises_received = 0

    @workflow.run
    async def run(self, input: TableMaintenanceWorkflowInput) -> None:  # noqa: A002
        """Run the plan's runs in order, waiting when each ends until its jobs are gone, then clean up and report."""
        operations: list[dict[str, Any]] = list(input.plan["operations"])
        try:
            for operation in operations:
                await self._run_operation(operation)
                await self._free_jobs_of(operation["operation"])
        finally:
            await self._finish(input.parent_workflow_id)

    @workflow.signal(name=TableMaintenanceSignal.OPERATION_RESULT)
    def operation_result(self, result: OperationResultSignal) -> None:
        """Store a Spark job result under its operation and attempt; drop one naming another run or no live attempt.

        A result is kept only for an attempt submitted and not yet cleaned up with its run. The attempt is
        logged before its submit, so a callback faster than the submit's reply is kept; an early result for
        a later run, whose attempt has not started, is dropped instead of ending that attempt once it starts.
        """
        if self._run_of.get(result.operation) != result.run_id:
            workflow.logger.warning("ignoring result of %s for run %s, not its run", result.operation, result.run_id)
            return
        if (result.operation, result.attempt) not in self._started_attempts:
            workflow.logger.warning(
                "ignoring result of %s attempt %s for run %s, no such attempt in flight",
                result.operation,
                result.attempt,
                result.run_id,
            )
            return
        self._results.setdefault((result.operation, result.attempt), result)

    @workflow.signal(name=TableMaintenanceSignal.RAISE_PRIORITY)
    def raise_priority(self, request: RaisePrioritySignal) -> None:
        """Keep a priority raise until the workflow applies it, and count it for the report."""
        self._raises_received += 1
        self._raise_requests.append(request)

    async def _run_operation(self, operation: dict[str, Any]) -> None:
        self._current = operation["operation"]
        size: str = operation["start_size"]
        for attempt in range(1, self._policy.max_attempts + 1):
            outcome = await self._run_attempt(operation, attempt, size)
            if (outcome.operation, outcome.attempt) in self._settled_attempts:
                return
            decision = await self._record_outcome(outcome)
            if outcome.succeeded:
                return
            if decision.get("status") == _PENDING:
                await self._skip(outcome.operation, outcome.error or _NOT_REACHED)
                return
            step = decision.get("next_step")
            if step not in (None, MaintenanceNextStep.RETRY_SAME):
                if step != MaintenanceNextStep.RETRY_LARGER:
                    return
                size = decision.get("next_size") or size
            if attempt < self._policy.max_attempts:
                await self._wait_to_retry(outcome.operation, attempt)

    async def _record_outcome(self, outcome: OperationResultSignal) -> dict[str, Any]:
        """Record the attempt's outcome and return the reply, empty when it was not recorded.

        A failure's record runs to its end even when the workflow is cancelled meanwhile, and the cancel
        goes on once it ended: a reply that retries left the run waiting to retry, with no attempt in flight
        whose record could end it, so the run is cancelled first (``cancel_maintenance_run``).
        """
        if outcome.succeeded:
            return await self._record(outcome) or {}
        reply, cancelled = await _to_the_end_noting_a_cancel(self._record(outcome))
        decision = reply or {}
        if cancelled:
            if _retries(decision):
                await self._cancel_waiting_run(outcome.operation)
            raise asyncio.CancelledError
        return decision

    async def _wait_to_retry(self, name: str, attempt: int) -> None:
        """Wait out the backoff after ``attempt``; a cancel meanwhile cancels the run of ``name``, then goes on.

        The run is waiting to retry, with no attempt in flight whose record could end it, so the cancel
        ends it itself (``cancel_maintenance_run``), even if another cancel arrives meanwhile.
        """
        try:
            await workflow.sleep(self._policy.backoff_after(attempt))
        except asyncio.CancelledError:
            await self._cancel_waiting_run(name)
            raise

    async def _run_attempt(self, operation: dict[str, Any], attempt: int, size: str) -> OperationResultSignal:
        name = operation["operation"]
        try:
            return await self._attempt_outcome(operation, attempt, size)
        except asyncio.CancelledError:
            if (name, attempt) not in self._settled_attempts:
                await self._record(self._failure(name, attempt, _CANCELLED, MaintenanceAttemptEnding.CANCELLED))
            if (name, attempt) in self._started_attempts:
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
        """Apply the raises that arrived, then submit the attempt's job and return its name.

        The submit's time is kept as the operation's latest submit, which a replacement moves on
        while the attempt's queue deadline stays with its first submit.
        """
        await self._apply_raises()
        name = operation["operation"]
        self._last_submit_at[name] = workflow.now()
        submitted = await self._activity(
            TableMaintenanceActivity.SUBMIT_MAINTENANCE_OPERATION,
            {"run_id": self._run_of[name], "operation": name, "attempt": attempt, "size": size, "now": _now()},
        )
        self._submitted.add(name)
        return submitted["job_name"]

    async def _await_outcome(
        self, operation: dict[str, Any], attempt: int, size: str, job_name: str
    ) -> OperationResultSignal:
        """Wait for the attempt to end: queued until its driver starts, then bounded by its deadline from that start.

        A raise that arrives meanwhile is applied at once. One that raised the run while the attempt
        is queued polls the job at once: a job that reads ``PENDING`` without a driver start is
        replaced (see ``_requeue``), keeping its submit time and its queue deadline; a driver start
        makes the attempt running; ``RUNNING`` without a start is left alone; and a failed, missing or
        completed job ends the attempt as any poll would. A poll that cannot read the status keeps the
        replacement wanted for the next poll. So does a job still ``SUBMITTING``: replacing it would let
        the submit under way create a driver under the replacement's name, whose own submit then fails;
        it is read again ``SUBMITTING_POLL_INTERVAL`` later within the fast window of its latest submit,
        at the queued pace after it.

        At the queue wait limit the job is polled once more: a driver start read then makes the attempt
        running, with its deadline from that start; a job ``RUNNING`` or ``COMPLETED`` whose start
        cannot be read is taken as started at that poll (the upper end of the clamp), so a completed
        one gets its callback grace and a running one its deadline; and a failed or missing job ends it
        as any poll would. Otherwise (a job still pending, or a status that cannot be read) the attempt
        is fenced and ends ``queue_timed_out``.
        """
        name = operation["operation"]
        key = (name, attempt)
        submitted_at = workflow.now()
        running_since: datetime | None = None
        deadline = submitted_at + self._policy.queue_wait_limit
        completed_since: datetime | None = None
        poll_at: datetime | None = None
        requeue_wanted = False
        polled_at_the_limit = False
        while True:
            if key in self._results:
                return self._results[key]
            now = workflow.now()
            at_the_limit = now >= deadline
            if at_the_limit and (running_since is not None or polled_at_the_limit):
                return await self._past_deadline(name, attempt, running=running_since is not None)
            if at_the_limit:
                polled_at_the_limit = True
            else:
                if poll_at is None:
                    in_fast_window = now - (running_since or submitted_at) < FAST_POLL_WINDOW
                    poll_at = now + _poll_interval(in_fast_window=in_fast_window, running=running_since is not None)
                await self._await_poll(key, min(poll_at, deadline) - now)
                if key in self._results:
                    return self._results[key]
                if self._raise_requests:
                    if await self._apply_raises() and running_since is None:
                        requeue_wanted = True
                        poll_at = workflow.now()
                    continue
                if workflow.now() >= deadline or workflow.now() < poll_at:
                    continue
            poll_at = None
            status = await self._job_status(name, attempt)
            if status is None:
                continue
            driver_started_at = status.get("started_running_at")
            if driver_started_at is None and at_the_limit and status["state"] in _STARTED_STATES:
                driver_started_at = workflow.now().isoformat()
            if running_since is None and driver_started_at:
                running_since = await self._started_running(name, attempt, driver_started_at, submitted_at)
                deadline = running_since + self._policy.attempt_deadline
            completed_since = (completed_since or workflow.now()) if status["state"] == "COMPLETED" else None
            ended = await self._ended_by_status(name, attempt, job_name, status, completed_since)
            if ended is not None:
                return ended
            if requeue_wanted and not at_the_limit:
                replaced, requeue_wanted, poll_at = await self._requeue_once_submitted(
                    operation, attempt, size, status, queued=running_since is None
                )
                if replaced is not None:
                    return replaced

    async def _await_poll(self, key: tuple[str, int], wait: timedelta) -> None:
        """Wait ``wait`` for the next poll, or less when the attempt's result or a raise arrives."""
        if wait <= timedelta(0):
            return
        try:
            await workflow.wait_condition(lambda: key in self._results or bool(self._raise_requests), timeout=wait)
        except TimeoutError:
            pass

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
            run_id=self._run_of[name],
            operation=name,
            attempt=attempt,
            succeeded=True,
            metrics={"completed_without_callback": 1},
            error=None,
        )

    async def _apply_raises(self) -> bool:
        """Apply the raises that arrived, in order, to every unfinished run; tell whether any raised the current one.

        Each raise is recorded on the current run first, then on each run after it, none of which has
        started, so a later run is submitted at the new priority too; each run keeps the higher
        priority. Only the current run's reply decides whether its queued attempt is replaced. A raise
        that fails to record on any run is logged and dropped, and the workflow then reports a raise
        unapplied. A raise leaves ``_raise_requests`` only once its records ended, so one a cancel
        interrupts is unapplied too.
        """
        raised = False
        while self._raise_requests:
            request = self._raise_requests[0]
            for name in self._unfinished_runs():
                reply = await self._raise_run(name, request)
                if name == self._current and reply is not None:
                    raised = raised or bool(reply["raised"])
            self._raise_requests.pop(0)
        return raised

    def _unfinished_runs(self) -> list[str]:
        """Return the operation of the current run and of every run after it, in plan order."""
        if self._current is None:
            return list(self._operations)
        return self._operations[self._operations.index(self._current) :]

    async def _raise_run(self, name: str, request: RaisePrioritySignal) -> dict[str, Any] | None:
        """Record a raise on the run of ``name`` and return its reply; a failed record is logged, marked and None."""
        run_id = self._run_of[name]
        try:
            reply = await self._activity(
                TableMaintenanceActivity.RAISE_MAINTENANCE_RUN_PRIORITY,
                {"run_id": run_id, "priority": request.priority, "now": _now()},
            )
        except ActivityError as error:
            _raise_if_cancelled(error)
            workflow.logger.warning("raising the priority of run %s failed: %s", run_id, error)
            self._dropped_raise = True
            return None
        workflow.logger.info(
            "raise to %s %s run %s, now at %s",
            request.priority or "the table's priority",
            "raised" if reply["raised"] else "left",
            run_id,
            reply["priority"],
        )
        return reply

    async def _requeue_once_submitted(
        self,
        operation: dict[str, Any],
        attempt: int,
        size: str,
        status: dict[str, Any],
        *,
        queued: bool,
    ) -> tuple[OperationResultSignal | None, bool, datetime | None]:
        """Requeue as ``_requeue_if_pending`` does, unless the job is still being submitted.

        Returns what the requeue ended the attempt with, whether the requeue is still wanted, and
        when to poll next (None for the usual pace). A queued job still ``SUBMITTING`` keeps the
        requeue wanted and is read again ``SUBMITTING_POLL_INTERVAL`` later within the fast window of
        its latest submit (a replacement's, after a requeue), ``QUEUED_POLL_INTERVAL`` after it, so a
        stuck submit stays cheap.
        """
        if queued and status["state"] == "SUBMITTING":
            in_fast_window = workflow.now() - self._last_submit_at[operation["operation"]] < FAST_POLL_WINDOW
            return None, True, workflow.now() + (SUBMITTING_POLL_INTERVAL if in_fast_window else QUEUED_POLL_INTERVAL)
        return await self._requeue_if_pending(operation, attempt, size, status, queued=queued), False, None

    async def _requeue_if_pending(
        self, operation: dict[str, Any], attempt: int, size: str, status: dict[str, Any], *, queued: bool
    ) -> OperationResultSignal | None:
        """Replace the attempt when it is still ``queued`` and its job reads ``PENDING``; see ``_requeue``.

        A job in any other state is not replaced: ``RUNNING`` without a driver start keeps running (a
        later poll reads the start), and a failed, missing or completed job was already handled as a
        poll handles it. Nor is an attempt whose result arrived during the poll.
        """
        if not queued or status["state"] != "PENDING" or (operation["operation"], attempt) in self._results:
            return None
        return await self._requeue(operation, attempt, size)

    async def _requeue(self, operation: dict[str, Any], attempt: int, size: str) -> OperationResultSignal | None:
        """Replace a pending attempt's job so it is queued again at the raised priority.

        The job is deleted, polled every fencing poll until it reads ``NOT_FOUND`` and has no live
        pods, then submitted again under the same attempt number. Returns None once it is queued
        again; a failure when the old job was not gone within the fencing confirm bound (recorded
        as an unconfirmed fence is, then polled slowly until gone) or the new submit failed.

        A driver that starts between the status read that found the job pending and the delete is
        killed with it; the attempt is then simply run again, which the maintenance procedures
        allow since they are idempotent. A result that killed job sent meanwhile is dropped before
        the new submit, so only the replacement's result ends the attempt.
        """
        name = operation["operation"]
        minutes = int(self._policy.fencing.confirm_bound.total_seconds() // 60)
        unconfirmed = await self._await_gone(
            name,
            attempt,
            job_gone=True,
            unconfirmed=lambda still: self._failure(
                name,
                attempt,
                f"{_NOT_REPLACED}: {still} {minutes} minutes after the priority raise",
                MaintenanceAttemptEnding.MISSING,
                still_running=True,
            ),
        )
        if unconfirmed is not None:
            return unconfirmed
        self._results.pop((name, attempt), None)
        try:
            await self._submit(operation, attempt, size)
        except ActivityError as error:
            _raise_if_cancelled(error)
            return self._submit_failed(name, attempt, error)
        return None

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
                    "run_id": self._run_of[name],
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
        """Fence the timed-out attempt."""
        return await self._fence(name, attempt, _TIMED_OUT, MaintenanceAttemptEnding.TIMED_OUT, since="the timeout")

    async def _missing(self, name: str, attempt: int) -> OperationResultSignal:
        """Fence an attempt whose job went missing, as its pods may outlive it."""
        return await self._fence(
            name, attempt, _MISSING, MaintenanceAttemptEnding.MISSING, since="the job went missing"
        )

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

        def unconfirmed_fence(still: str) -> OperationResultSignal:
            error = f"{reason}; {still} {minutes} minutes after {since}"
            return self._failure(name, attempt, error, ending, still_running=True)

        unconfirmed = await self._await_gone(name, attempt, unconfirmed=unconfirmed_fence if bounded else None)
        return unconfirmed or self._failure(name, attempt, reason, ending)

    async def _await_gone(
        self,
        name: str,
        attempt: int,
        *,
        unconfirmed: Callable[[str], OperationResultSignal] | None,
        job_gone: bool = False,
    ) -> OperationResultSignal | None:
        """Delete an attempt's job and poll until its pods (and, with ``job_gone``, the job) are gone.

        Returns None when they were gone within the confirm bound. Otherwise, when bounded (an
        ``unconfirmed`` given), the attempt is recorded at the bound as the failure ``unconfirmed``
        builds from what was still there, polling goes on slower until they are gone, and that
        failure is returned. Unbounded, nothing is recorded and the wait lasts however long they take,
        slower once past the bound.
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
            if unconfirmed is not None and key not in self._settled_attempts and workflow.now() >= confirm_by:
                if not deleted:
                    still = "its job could still not be deleted"
                elif not job_absent:
                    still = "its job was still there"
                else:
                    still = "its pods were still running"
                outcome = unconfirmed(still)
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
                {"run_id": self._run_of[name], "operation": name, "attempt": attempt},
            )
        except ActivityError as error:
            _raise_if_cancelled(error)
            workflow.logger.warning("deleting the job of %s attempt %s failed: %s", name, attempt, error)
            return False
        return True

    async def _pods_gone(self, name: str, attempt: int) -> bool:
        try:
            pods = await self._activity(
                TableMaintenanceActivity.GET_MAINTENANCE_JOB_PROCESSES,
                {"run_id": self._run_of[name], "operation": name, "attempt": attempt},
            )
        except ActivityError as error:
            _raise_if_cancelled(error)
            workflow.logger.warning("pods of %s attempt %s unknown: %s", name, attempt, error)
            return False
        return not pods["live_processes"]

    async def _job_status(self, name: str, attempt: int) -> dict[str, Any] | None:
        try:
            return await self._activity(
                TableMaintenanceActivity.GET_MAINTENANCE_JOB_STATUS,
                {"run_id": self._run_of[name], "operation": name, "attempt": attempt},
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

    async def _free_jobs_of(self, name: str) -> None:
        """Delete the job of every attempt of the run of ``name``, once that run ended, and wait until all are gone.

        This keeps one Spark job of the table at a time and frees the executors kept for evidence
        before the next run's job queues (see ``_await_jobs_gone``).
        """
        await self._await_jobs_gone([(n, a) for n, a in self._started_attempts if n == name])

    async def _await_jobs_gone(self, attempts: list[tuple[str, int]]) -> None:
        """Delete each attempt's job and wait until it reads ``NOT_FOUND`` with no live pods, recording nothing.

        The wait is a fence's (``_await_gone``), unbounded: its run already ended, so there is no attempt
        left to fail, and it lasts however long the job takes to go, polling slower past the confirm bound.
        """
        for name, attempt in attempts:
            await self._await_gone(name, attempt, unconfirmed=None, job_gone=True)
            self._started_attempts.remove((name, attempt))

    async def _finish(self, parent_workflow_id: str) -> None:
        """Free the started jobs still left, skip every run of the plan not started, then report to the parent.

        The jobs still left (those of a run a cancel interrupted) are waited for until gone, as after a run,
        even if another cancel arrives meanwhile.
        A run has started once one of its submits returned. Every run exists (the parent created them all
        before it started this workflow), so a run the workflow never reached is skipped, and so is one none
        of whose submits returned (a submit a cancel interrupted may never have left the run pending); a
        skip leaves a run that did leave pending as it is. A failed skip, a run not found included, is logged.
        """
        if self._started_attempts:
            await _to_the_end(self._await_jobs_gone(list(self._started_attempts)))
        for name in self._operations:
            if name not in self._submitted and name not in self._skipped:
                await self._skip(name)
        try:
            await self._activity(
                TableMaintenanceActivity.SIGNAL_PARENT,
                {
                    "workflow_id": parent_workflow_id,
                    "signal": TableReconciliationSignal.MAINTENANCE_FINISHED,
                    "arg": {
                        "run_ids": self._run_ids,
                        "record_failures": self._record_failures,
                        "unapplied_raise": self._dropped_raise or bool(self._raise_requests),
                        "raises_received": self._raises_received,
                    },
                },
            )
        except ActivityError as error:
            workflow.logger.warning("signalling the parent failed: %s", error)
        await workflow.wait_condition(workflow.all_handlers_finished)

    async def _skip(self, name: str, reason: str = _NOT_REACHED) -> None:
        """Skip the run of ``name``, saying why; a failed skip is logged."""
        self._skipped.add(name)
        run_id = self._run_of[name]
        try:
            await self._activity(
                TableMaintenanceActivity.SKIP_MAINTENANCE_RUN,
                {"run_id": run_id, "reason": reason, "now": _now()},
            )
        except ActivityError as error:
            workflow.logger.warning("skipping run %s failed: %s", run_id, error)

    async def _cancel_waiting_run(self, name: str) -> None:
        """Cancel the run of ``name``, which has no attempt in flight; a failed cancel is logged."""
        run_id = self._run_of[name]
        try:
            await _to_the_end(
                self._activity(TableMaintenanceActivity.CANCEL_MAINTENANCE_RUN, {"run_id": run_id, "now": _now()})
            )
        except ActivityError as error:
            workflow.logger.warning("cancelling run %s failed: %s", run_id, error)

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
            run_id=self._run_of[name],
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
            start_to_close_timeout=_ACTIVITIES.start_to_close,
            retry_policy=_ACTIVITIES.retry_policy(),
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


async def _to_the_end_noting_a_cancel[T](work: Coroutine[Any, Any, T]) -> tuple[T, bool]:
    """Run ``work`` to its end even when the workflow is cancelled while it runs, and tell whether it was."""
    task = asyncio.ensure_future(work)
    cancelled = False
    while True:
        try:
            return await asyncio.shield(task), cancelled
        except asyncio.CancelledError:
            if task.cancelled():
                raise
            cancelled = True


def _retries(decision: dict[str, Any]) -> bool:
    """Tell whether a record's reply left the run waiting to retry."""
    return decision.get("status") == _RETRY_WAITING or decision.get("next_step") in _RETRYING_STEPS


def _raise_if_cancelled(error: ActivityError) -> None:
    """Turn an activity cancelled by a workflow cancellation back into the cancel."""
    if is_cancelled_exception(error):
        raise asyncio.CancelledError from error
