"""Define the TableReconciliationWorkflow."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy, SearchAttributePair, TypedSearchAttributes, WorkflowIDReusePolicy
from temporalio.exceptions import ActivityError, FailureError, is_cancelled_exception
from temporalio.workflow import ParentClosePolicy

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    DEFAULT_ATTEMPT_DEADLINE_SECONDS,
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_QUEUE_WAIT_LIMIT_SECONDS,
    TABLE_MAINTENANCE_WORKFLOW,
    RaisePrioritySignal,
    TableMaintenanceSignal,
    TableMaintenanceWorkflowInput,
    table_maintenance_summary,
    table_maintenance_workflow_id,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TABLE_RECONCILIATION_WORKFLOW,
    TableReconciliationActivity,
    TableReconciliationSignal,
    TableReconciliationWorkflowInput,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows.mint_workflow_prefixed_id import (
    mint_workflow_prefixed_id,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows.table_maintenance_activity_policy import (
    TableMaintenanceActivityPolicy,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows.table_maintenance_attempt_policy import (
    TableMaintenanceAttemptPolicy,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows.table_search_attribute_keys import (
    TableSearchAttributeKeys,
)

_ACTIVITY_TIMEOUT = timedelta(minutes=2)
_ACTIVITY_RETRY = RetryPolicy(maximum_attempts=5, initial_interval=timedelta(seconds=2), backoff_coefficient=2.0)
_IN_FLIGHT_MARGIN = timedelta(hours=1)
_CANCEL_GRACE = timedelta(minutes=15)
_ENDING_REASONS = frozenset({"dropped", "unmanaged"})
_TRIGGER_SCHEDULED = "scheduled"
_TRIGGER_MANUAL = "manual"
_REASON_SCHEDULE = "schedule"
_REASON_CATALOG_COMMIT = "catalog_commit"
_REASON_DISCOVERY_SCAN = "discovery_scan"
_REASON_POLICY_CHANGED = "policy_changed"
_REASON_MANUAL_RUN = "manual_run"
_REASON_RECONCILE_NOW = "reconcile_now"
_REASON_PREVIOUS_RUN_FINISHED = "previous_run_finished"
_SEARCH_ATTRIBUTES_PATCH = "table-search-attributes"
_FENCED_BOUND_PATCH = "fencing-in-flight-bound"
_AWAIT_CLOSE_PATCH = "await-cancelled-run-close"
_PREFIXED_IDS_PATCH = "prefixed-run-and-reconciliation-ids"
_CLOSING_BOUND = TableMaintenanceActivityPolicy().worst_case()
_CLOSING_POLL = timedelta(seconds=5)
_RUN_ID_PREFIX = "mr"
_RECONCILIATION_ID_PREFIX = "rc"
_OLDER_PLAN_INTERVAL_KEY = "reconcile_interval_seconds"


@workflow.defn(name=TABLE_RECONCILIATION_WORKFLOW)
class TableReconciliationWorkflow:
    """Plan and start the maintenance runs of one table, one run at a time.

    The loop wakes on its timer (the table's schedule interval, from the last
    plan; one hour at first) or on any signal, and then asks
    ``plan_table_maintenance``, which reloads the table: the database is the
    authority on whether the table is managed and the policy applies at plan
    time, so a policy change only wakes the loop.
    A non-empty plan starts a ``TableMaintenanceWorkflow`` child that outlives this run
    (``ABANDON``) and reports back only through ``maintenance_finished``, which is
    why the run in flight survives continue-as-new. While a run is in flight
    nothing is planned. A ``trigger_now`` then raises the priority of the run in
    flight instead of starting another: the child is signalled ``raise_priority``
    with the trigger's priority (none means the table's), and a delivered signal
    consumes the trigger and takes its ``manual_run`` off the wake reasons. The
    consumed trigger is kept with the run in flight (through continue-as-new), and
    given back, counted ``manual_run`` again, when the run reports the raise
    unapplied (``unapplied_raise``) or reports fewer raises received
    (``raises_received``) than were delivered to it (counted through
    continue-as-new), since those reached it after it built its report. A trigger
    whose signal cannot be delivered, or whose run reported while the signal was
    on its way, is kept and planned once the run finishes. A run whose child
    closed without reporting is treated as finished, and its consumed trigger
    given back: a child this execution started is noticed when its handle
    resolves (a closed one is never carried through continue-as-new), and one
    carried through continue-as-new when a raise cannot reach it and a lookup
    (``get_workflow_running``) finds it no longer running, otherwise at the
    give-up. A run given up gives its consumed trigger back whether or not it
    reports, since the cancel stopped its work. A
    run that never reports back is given up once the child's worst case has passed
    (per planned operation: every attempt waiting out the queue wait limit the plan
    carried, 24 hours for a plan without one, then timing out after the attempt
    deadline the plan carried, six hours for a plan without one, and being fenced
    for 15 minutes, plus the backoffs, plus 1 h): the child is cancelled first (by the
    workflow ID recorded when it started, the table's maintenance workflow ID),
    so its cleanup fences its live attempt, records the result
    and deletes its Spark job, and its report is
    awaited for as long as the child still runs (less if the cancel fails
    because the child is gone or no workflow ID was recorded), so a new run does
    not overlap the old one's Spark job. A skip
    because the table was dropped or unmanaged, or a
    ``stop`` signal, ends the workflow once no run is in flight, but never on a
    stale decision (R31): any other signal after ``stop`` cancels the stop, and a
    wake that arrives while a plan says dropped or unmanaged makes it plan again.

    Every wake also counts its reason (a due plan timer counts ``schedule``;
    ``stop`` counts nothing), except a catalog commit, which is debounced. The
    first commit not yet covered by a check opens a window of the plan's
    ``catalog_commit_debounce_seconds`` (five minutes before the first plan);
    later commits join it without moving its end, so a table written every
    minute is still checked once per window, and when it closes its commits are
    counted ``catalog_commit`` and checked. A check for any other reason before
    then takes the open window with it, and a window that closes while a run is
    in flight is checked after the run. With no ``catalog_commit`` in the policy
    (debounce ``None``) a commit opens no window and counts nothing, but still
    cancels a ``stop``. The open window and its commits survive continue-as-new.
    The reasons accumulate, through runs in flight and
    continue-as-new, until the next plan takes them; reasons that arrive while
    a plan is running belong to the plan they wake next. After each plan that
    found the table, ``record_table_reconciliation`` stores the reconciliation
    with those reasons, the plan's checks and the run it started (or that its
    start failed). The run id is generated with the reconciliation id before
    planning, so the record and the run agree. A failed plan records nothing
    and drops its reasons; a failed record is logged and the loop goes on.
    Each run ends once, counted as ``previous_run_finished``: when its
    ``maintenance_finished`` arrives or when it is given up, whichever comes
    first (a report after the give-up is ignored). The loop never plans
    without a reason: a wake that leaves no reason and finds the plan timer not
    yet due (such as a stale wake left by a report during the give-up grace)
    goes back to waiting. A plan with operations that is not started because the workflow is stopping
    is not recorded either, since its due operations neither started nor
    failed to start.

    The workflow tags itself with its table UUID when it starts, and with the
    table name each plan reports when that name changed, and starts each run
    tagged with the table, its planned operations and its trigger, so a table's
    workflows can be found by search attribute. A run that started before these
    tags existed (patch ``table-search-attributes``) carries none until its next
    continue-as-new.

    The next plan always comes one schedule interval after the last. A plan
    names no run: it claims nothing for the run it starts, and a run that is not
    started leaves nothing to hand back.

    A run that reported may still be open: its report activity completes, and is
    retried, after the report landed. The next run is started under the same
    workflow id only once that execution closed: awaited through the child handle
    of a run this execution started, looked up every 5 seconds
    (``get_workflow_running``) for one carried through continue-as-new, and for at
    most the report activity's worst case (``TableMaintenanceActivityPolicy``),
    after which the start is tried and, if refused, recorded as a failed start. A
    ``stop`` that arrives during that wait starts no run, and the plan is not
    recorded, like one planned while stopping. A manual trigger is consumed only
    by a run that started, so a refused start keeps it pending for the next plan.

    Each pass mints its reconciliation id (``rc-``) and the run id it would start under (``mr-``)
    from the workflow's clock and random source (patch ``prefixed-run-and-reconciliation-ids``); a
    history from before prefixed ids replays with the UUIDs it minted then.
    """

    @workflow.init
    def __init__(self, input: TableReconciliationWorkflowInput) -> None:  # noqa: A002
        """Restore the in-flight run, the pending manual trigger and the timer."""
        self._table_uuid = input.table_uuid
        self._in_flight_run_id = input.in_flight_run_id
        self._in_flight_workflow_id = input.in_flight_workflow_id
        self._in_flight_started_at: datetime | None = None
        if input.in_flight_started_at:
            self._in_flight_started_at = datetime.fromisoformat(input.in_flight_started_at)
        elif input.in_flight_run_id is not None:
            self._in_flight_started_at = workflow.now()
        self._in_flight_operations = input.in_flight_operation_count
        self._in_flight_attempt_deadline_seconds = input.in_flight_attempt_deadline_seconds
        self._in_flight_max_attempts = input.in_flight_max_attempts
        self._in_flight_queue_wait_limit_seconds = input.in_flight_queue_wait_limit_seconds
        self._pending_manual = None if input.pending_manual is None else list(input.pending_manual)
        self._pending_manual_priority = input.pending_manual_priority
        self._raised_manual = None if input.raised_manual is None else list(input.raised_manual)
        self._raised_manual_priority = input.raised_manual_priority
        self._raises_delivered = input.raises_delivered
        self._closing_workflow_id = input.closing_workflow_id
        self._closing_handle: workflow.ChildWorkflowHandle[Any, Any] | None = None
        self._child_handle: workflow.ChildWorkflowHandle[Any, Any] | None = None
        self._next_plan_at = datetime.fromisoformat(input.next_plan_at) if input.next_plan_at else None
        self._continue_as_new_after = input.continue_as_new_after
        self._interval = timedelta(seconds=input.schedule_interval_seconds)
        self._commit_debounce = _seconds_or_none(input.catalog_commit_debounce_seconds)
        self._commit_window_closes_at: datetime | None = None
        if input.commit_window_closes_at:
            self._commit_window_closes_at = datetime.fromisoformat(input.commit_window_closes_at)
        self._pending_commits = input.pending_commits
        self._wake_reasons: dict[str, int] = dict(input.wake_reasons or {})
        self._woken = False
        self._stopping = False
        self._planning = False
        self._signals_handled = 0
        self._cancel_failed = False
        self._cancel_task: asyncio.Task[None] | None = None
        self._given_up_run_id: str | None = None

    @workflow.run
    async def run(self, input: TableReconciliationWorkflowInput) -> None:  # noqa: A002
        """Wait, plan and start runs until the table leaves maintenance."""
        if self._next_plan_at is None:
            self._next_plan_at = workflow.now() + self._interval
        if self._tags_table():
            workflow.upsert_search_attributes([TableSearchAttributeKeys.TABLE_UUID.value_set(self._table_uuid)])
        iterations = 0
        while True:
            if self._stopping and self._in_flight_run_id is None:
                return
            if self._should_continue_as_new(iterations):
                await workflow.wait_condition(workflow.all_handlers_finished)
                if not self._woken and not self._child_closed():
                    workflow.continue_as_new(self._carry())
            await self._wait()
            self._woken = False
            iterations += 1
            self._end_closed_child()
            if self._in_flight_run_id is not None:
                await self._give_up_stuck_run()
            if self._in_flight_run_id is not None and self._pending_manual is not None:
                await self._raise_in_flight()
            if self._in_flight_run_id is None and not self._stopping and self._has_reason_to_plan():
                ends = await self._plan_and_start()
                if ends and not self._woken:
                    return

    @workflow.signal(name=TableReconciliationSignal.POLICY_CHANGED)
    def policy_changed(self, payload: dict | None = None) -> None:
        """Wake the loop to re-plan with the policy that now applies."""
        self._wake(_REASON_POLICY_CHANGED, cancels_stop=True)

    @workflow.signal(name=TableReconciliationSignal.TABLE_UPDATED)
    def table_updated(self, payload: dict | None = None) -> None:
        """Count a catalog commit in the open window, opening one if none is, and wake the loop to re-arm its timer.

        Without ``catalog_commit`` in the policy the commit counts nothing, but still cancels a ``stop`` (R31).
        """
        if self._commit_debounce is not None:
            self._pending_commits += 1
            if self._commit_window_closes_at is None:
                self._commit_window_closes_at = workflow.now() + self._commit_debounce
        self._wake(None, cancels_stop=True)

    @workflow.signal(name=TableReconciliationSignal.TABLE_SEEN)
    def table_seen(self, payload: dict | None = None) -> None:
        """Wake the loop because a discovery scan saw the table."""
        self._wake(_REASON_DISCOVERY_SCAN, cancels_stop=True)

    @workflow.signal(name=TableReconciliationSignal.TRIGGER_NOW)
    def trigger_now(self, payload: dict | None = None) -> None:
        """Keep a manual trigger, replacing any pending one, and wake the loop."""
        operations = (payload or {}).get("operations") or []
        self._pending_manual = [str(op) for op in operations]
        self._pending_manual_priority = (payload or {}).get("priority")
        self._wake(_REASON_MANUAL_RUN, cancels_stop=True)

    @workflow.signal(name=TableReconciliationSignal.RECONCILE_NOW)
    def reconcile_now(self, payload: dict | None = None) -> None:
        """Wake the loop to reconcile by the normal rules, after any run in flight."""
        self._wake(_REASON_RECONCILE_NOW, cancels_stop=True)

    @workflow.signal(name=TableReconciliationSignal.STOP)
    def stop(self, payload: dict | None = None) -> None:
        """End the workflow once no run is in flight; plan nothing more."""
        self._stopping = True
        self._wake(None, cancels_stop=False)

    @workflow.signal(name=TableReconciliationSignal.MAINTENANCE_FINISHED)
    def maintenance_finished(self, payload: dict | None = None) -> None:
        """Clear the in-flight run it reports; ignore any other run id."""
        self._signals_handled += 1
        run_id = (payload or {}).get("run_id")
        if run_id is None or run_id != self._in_flight_run_id:
            workflow.logger.warning("ignoring maintenance_finished of run %s", run_id)
            return
        if run_id == self._given_up_run_id or self._raise_missed(payload or {}):
            self._give_back_raised_manual(run_id)
        self._closing_workflow_id = self._in_flight_workflow_id
        self._closing_handle = self._child_handle
        self._clear_in_flight()
        self._count(_REASON_PREVIOUS_RUN_FINISHED)
        self._woken = True

    def _raise_missed(self, report: dict[str, Any]) -> bool:
        """Tell whether the run's report leaves a raise of it unapplied.

        The run says so (``unapplied_raise``), or it received fewer raises than were delivered to it:
        those arrived after it built its report. A report without ``raises_received`` counts only
        its own word.
        """
        if report.get("unapplied_raise", False):
            return True
        received = report.get("raises_received")
        return received is not None and self._raises_delivered > received

    @workflow.query
    def state(self) -> dict[str, Any]:
        """Report the run in flight, the manual trigger, the timer, the commit window, the wake reasons and the loop."""
        return {
            "in_flight_run_id": self._in_flight_run_id,
            "in_flight_workflow_id": self._in_flight_workflow_id,
            "in_flight_started_at": _iso(self._in_flight_started_at),
            "pending_manual": self._pending_manual,
            "pending_manual_priority": self._pending_manual_priority,
            "raised_manual": self._raised_manual,
            "raised_manual_priority": self._raised_manual_priority,
            "closing_workflow_id": self._closing_workflow_id,
            "raises_delivered": self._raises_delivered,
            "stopping": self._stopping,
            "next_plan_at": _iso(self._next_plan_at),
            "schedule_interval_seconds": int(self._interval.total_seconds()),
            "catalog_commit_debounce_seconds": _whole_seconds_or_none(self._commit_debounce),
            "commit_window_closes_at": _iso(self._commit_window_closes_at),
            "pending_commits": self._pending_commits,
            "woken": self._woken,
            "wake_reasons": dict(self._wake_reasons),
            "planning": self._planning,
            "signals_handled": self._signals_handled,
        }

    def _tags_table(self) -> bool:
        """Tell whether this run tags its workflows with the table search attributes."""
        return workflow.patched(_SEARCH_ATTRIBUTES_PATCH)

    def _tag_table_name(self, table_name: str | None) -> None:
        """Upsert the table name a plan reports when it differs from the one the workflow carries."""
        if not table_name or not self._tags_table():
            return
        if workflow.info().typed_search_attributes.get(TableSearchAttributeKeys.TABLE_NAME) == table_name:
            return
        workflow.upsert_search_attributes([TableSearchAttributeKeys.TABLE_NAME.value_set(table_name)])

    def _wake(self, reason: str | None, *, cancels_stop: bool) -> None:
        """Wake the loop and count the reason; a decision signal after ``stop`` supersedes it (R31)."""
        self._signals_handled += 1
        if cancels_stop:
            self._stopping = False
        if reason is not None:
            self._count(reason)
        self._woken = True

    def _has_reason_to_plan(self) -> bool:
        """Count a due plan timer and a closed commit window; tell whether any reason calls for a plan.

        ``schedule`` is counted here, once per plan. While a run is in flight the loop's timer is
        that run's deadline, so a give-up is not a schedule wake; a tick that came due during the
        run is counted when the run ends, which is why the plan after a run can carry
        {previous_run_finished: 1, schedule: 1} without counting twice. A commit window that closed
        during the run is counted the same way.
        """
        now = workflow.now()
        if self._next_plan_at is not None and now >= self._next_plan_at:
            self._count(_REASON_SCHEDULE)
        if self._commit_window_closes_at is not None and now >= self._commit_window_closes_at:
            self._take_commit_window()
        return bool(self._wake_reasons)

    def _take_commit_window(self) -> None:
        """Close the open commit window, counting its commits as ``catalog_commit``."""
        if self._pending_commits > 0:
            reasons = self._wake_reasons
            reasons[_REASON_CATALOG_COMMIT] = reasons.get(_REASON_CATALOG_COMMIT, 0) + self._pending_commits
        self._pending_commits = 0
        self._commit_window_closes_at = None

    def _count(self, reason: str) -> None:
        self._wake_reasons[reason] = self._wake_reasons.get(reason, 0) + 1

    def _should_continue_as_new(self, iterations: int) -> bool:
        if self._stopping:
            return False
        return workflow.info().is_continue_as_new_suggested() or iterations >= self._continue_as_new_after

    def _carry(self) -> TableReconciliationWorkflowInput:
        return TableReconciliationWorkflowInput(
            table_uuid=self._table_uuid,
            in_flight_run_id=self._in_flight_run_id,
            in_flight_workflow_id=self._in_flight_workflow_id,
            in_flight_started_at=_iso(self._in_flight_started_at),
            in_flight_operation_count=self._in_flight_operations,
            pending_manual=self._pending_manual,
            pending_manual_priority=self._pending_manual_priority,
            next_plan_at=_iso(self._next_plan_at),
            schedule_interval_seconds=int(self._interval.total_seconds()),
            continue_as_new_after=self._continue_as_new_after,
            wake_reasons=dict(self._wake_reasons),
            in_flight_attempt_deadline_seconds=self._in_flight_attempt_deadline_seconds,
            in_flight_max_attempts=self._in_flight_max_attempts,
            in_flight_queue_wait_limit_seconds=self._in_flight_queue_wait_limit_seconds,
            raised_manual=self._raised_manual,
            raised_manual_priority=self._raised_manual_priority,
            closing_workflow_id=self._closing_workflow_id,
            raises_delivered=self._raises_delivered,
            catalog_commit_debounce_seconds=_whole_seconds_or_none(self._commit_debounce),
            commit_window_closes_at=_iso(self._commit_window_closes_at),
            pending_commits=self._pending_commits,
        )

    async def _wait(self) -> None:
        """Wait for a wake or the timer: the deadline of a run in flight, else the plan timer or the window end."""
        wake_at = self._in_flight_deadline()
        if self._in_flight_run_id is None:
            wake_at = _earliest(self._next_plan_at, self._commit_window_closes_at)
        timeout = None if wake_at is None else wake_at - workflow.now()
        if timeout is not None and timeout <= timedelta(0):
            return
        try:
            await workflow.wait_condition(lambda: self._woken or self._child_closed(), timeout=timeout)
        except TimeoutError:
            pass

    def _child_closed(self) -> bool:
        """Tell whether the run in flight's child, started by this execution, has closed."""
        return self._child_handle is not None and self._child_handle.done()

    def _in_flight_deadline(self) -> datetime | None:
        if self._in_flight_run_id is None or self._in_flight_started_at is None:
            return None
        started_at = self._in_flight_started_at
        return started_at + self._in_flight_per_operation() * max(self._in_flight_operations, 1)

    def _in_flight_per_operation(self) -> timedelta:
        """Return how long one operation of the run in flight may take: its worst case plus 1 h.

        The worst case counts the queue wait and the fencing of every attempt; a history from before
        fencing (patch ``fencing-in-flight-bound``) keeps the unfenced bound it gave
        runs up on.
        """
        attempt_deadline = timedelta(seconds=self._in_flight_attempt_deadline_seconds)
        policy = TableMaintenanceAttemptPolicy(
            max_attempts=self._in_flight_max_attempts,
            attempt_deadline=attempt_deadline,
            queue_wait_limit=timedelta(seconds=self._in_flight_queue_wait_limit_seconds),
        )
        if workflow.patched(_FENCED_BOUND_PATCH):
            return policy.operation_worst_case() + _IN_FLIGHT_MARGIN
        return policy.unfenced_operation_worst_case() + _IN_FLIGHT_MARGIN

    async def _give_up_stuck_run(self) -> None:
        """Cancel a run past its budget, await its report, then forget it.

        The cancel request runs as its own task: a request the server never
        resolves must not block the loop, and a failed one (the child is missing
        or closed, so nothing can report back) ends the wait at once. The
        cancelled child fences its live attempt before it reports, which can
        take as long as its pods do, so no new run starts until it reported or
        closed: every 15 minutes without a report the child is looked up, and
        only a child that is no longer running is forgotten. A history from
        before this (patch ``await-cancelled-run-close``) forgets the run after
        one 15 minute grace. The cancel stopped the run's work, so the manual
        trigger a raise of it consumed is given back whether it reports or not.
        """
        deadline = self._in_flight_deadline()
        run_id = self._in_flight_run_id
        if run_id is None or deadline is None or workflow.now() < deadline:
            return
        workflow.logger.warning("maintenance run %s never reported back; cancelling it", run_id)
        workflow_id = self._in_flight_workflow_id
        self._given_up_run_id = run_id
        self._cancel_failed = False
        self._cancel_task = asyncio.create_task(self._cancel_child(run_id, workflow_id))
        awaits_close = workflow.patched(_AWAIT_CLOSE_PATCH)
        while True:
            try:
                await workflow.wait_condition(
                    lambda: self._in_flight_run_id != run_id or self._cancel_failed,
                    timeout=_CANCEL_GRACE,
                )
                break
            except TimeoutError:
                if not awaits_close or workflow_id is None or not await self._still_running(workflow_id):
                    workflow.logger.warning("cancelled run %s did not report back; no longer waiting", run_id)
                    break
                workflow.logger.warning("cancelled run %s is still running; waiting for it", run_id)
        self._given_up_run_id = None
        if self._in_flight_run_id == run_id:
            self._end_unreported_run(run_id, "it was given up and did not report back")

    async def _still_running(self, workflow_id: str) -> bool:
        """Tell whether a cancelled child still runs; a failed lookup counts as running."""
        try:
            looked_up = await workflow.execute_activity(
                TableReconciliationActivity.GET_WORKFLOW_RUNNING,
                {"workflow_id": workflow_id},
                start_to_close_timeout=_ACTIVITY_TIMEOUT,
                retry_policy=_ACTIVITY_RETRY,
            )
        except ActivityError as error:
            if is_cancelled_exception(error):
                raise asyncio.CancelledError from error
            workflow.logger.warning("looking up workflow %s failed: %s", workflow_id, error)
            return True
        return bool(looked_up["running"])

    async def _cancel_child(self, run_id: str, workflow_id: str | None) -> None:
        if workflow_id is None:
            workflow.logger.info("run %s has no recorded workflow to cancel", run_id)
            self._cancel_failed = True
            return
        handle = workflow.get_external_workflow_handle(workflow_id)
        try:
            await handle.cancel()
        except FailureError as error:
            workflow.logger.info("run %s could not be cancelled: %s", run_id, error)
            if self._in_flight_run_id == run_id:
                self._cancel_failed = True

    async def _raise_in_flight(self) -> None:
        """Ask the run in flight to raise its priority for the pending manual trigger.

        A delivered signal consumes the trigger (unless another replaced it meanwhile), keeps it
        with the run in flight in case the run reports the raise unapplied, and takes one
        ``manual_run`` off the wake reasons, since no plan follows it. A signal that fails (the
        child is gone or no workflow ID was recorded), or one delivered to a run that reported
        meanwhile, leaves the trigger pending, to be planned once the run reports (or at once).
        """
        manual = self._pending_manual
        priority = self._pending_manual_priority
        run_id = self._in_flight_run_id
        workflow_id = self._in_flight_workflow_id
        if workflow_id is None:
            workflow.logger.info("run %s has no recorded workflow to raise; keeping the manual trigger", run_id)
            return
        handle = workflow.get_external_workflow_handle(workflow_id)
        try:
            await handle.signal(TableMaintenanceSignal.RAISE_PRIORITY, RaisePrioritySignal(priority))
        except FailureError as error:
            if is_cancelled_exception(error):
                raise asyncio.CancelledError from error
            workflow.logger.info("raising the priority of run %s failed: %s; keeping the manual trigger", run_id, error)
            await self._forget_if_gone(run_id, workflow_id)
            return
        if self._in_flight_run_id != run_id:
            workflow.logger.info("run %s reported while its raise was on the way; keeping the manual trigger", run_id)
            return
        self._raises_delivered += 1
        workflow.logger.info("raised the priority of run %s for manual trigger %s", run_id, manual)
        if self._pending_manual is manual:
            self._raised_manual, self._raised_manual_priority = manual, priority
        self._consume_manual(manual, None)
        self._uncount(_REASON_MANUAL_RUN)

    async def _forget_if_gone(self, run_id: str | None, workflow_id: str) -> None:
        """End a run carried through continue-as-new whose workflow no longer runs, as if it had reported.

        A run this execution started has a child handle, and its close ends it through ``_wait``.
        """
        if self._child_handle is not None or await self._still_running(workflow_id):
            return
        if run_id is not None and self._in_flight_run_id == run_id:
            self._end_unreported_run(run_id, f"its workflow {workflow_id} is no longer running")

    def _end_closed_child(self) -> None:
        """End the run in flight whose child closed without reporting, as if it had reported."""
        run_id = self._in_flight_run_id
        if run_id is None or not self._child_closed():
            return
        self._end_unreported_run(run_id, "its workflow closed without reporting")

    def _end_unreported_run(self, run_id: str, why: str) -> None:
        """Treat a run that will never report as finished, giving back the manual trigger its raise consumed."""
        workflow.logger.warning("maintenance run %s ended: %s", run_id, why)
        self._give_back_raised_manual(run_id)
        self._clear_in_flight()
        self._count(_REASON_PREVIOUS_RUN_FINISHED)

    def _give_back_raised_manual(self, run_id: str) -> None:
        """Make the manual trigger a raise of ``run_id`` consumed pending again, unless a newer one is."""
        if self._raised_manual is None:
            return
        if self._pending_manual is not None:
            workflow.logger.info("run %s may have left a raise unapplied; a newer manual trigger is pending", run_id)
            return
        workflow.logger.info(
            "run %s may have left its raise unapplied; planning manual trigger %s", run_id, self._raised_manual
        )
        self._pending_manual = self._raised_manual
        self._pending_manual_priority = self._raised_manual_priority
        self._count(_REASON_MANUAL_RUN)

    def _uncount(self, reason: str) -> None:
        count = self._wake_reasons.get(reason, 0) - 1
        if count > 0:
            self._wake_reasons[reason] = count
        else:
            self._wake_reasons.pop(reason, None)

    async def _await_closing(self) -> None:
        """Wait, for at most the closing bound, until the run that reported last has closed.

        A run this execution started is awaited through its child handle; one carried through
        continue-as-new is looked up every few seconds (a failed lookup counts as still running).
        """
        workflow_id = self._closing_workflow_id
        if workflow_id is None:
            return
        handle = self._closing_handle
        closes_by = workflow.now() + _CLOSING_BOUND
        if handle is not None:
            if not handle.done():
                try:
                    await workflow.wait_condition(handle.done, timeout=_CLOSING_BOUND)
                except TimeoutError:
                    workflow.logger.warning("workflow %s did not close after its report; starting anyway", workflow_id)
        else:
            while await self._still_running(workflow_id):
                if workflow.now() >= closes_by:
                    workflow.logger.warning("workflow %s did not close after its report; starting anyway", workflow_id)
                    break
                await workflow.sleep(_CLOSING_POLL)
        self._closing_workflow_id = None
        self._closing_handle = None

    def _clear_in_flight(self) -> None:
        self._in_flight_run_id = None
        self._in_flight_workflow_id = None
        self._in_flight_started_at = None
        self._in_flight_operations = 0
        self._in_flight_attempt_deadline_seconds = DEFAULT_ATTEMPT_DEADLINE_SECONDS
        self._in_flight_max_attempts = DEFAULT_MAX_ATTEMPTS
        self._in_flight_queue_wait_limit_seconds = DEFAULT_QUEUE_WAIT_LIMIT_SECONDS
        self._raised_manual = None
        self._raised_manual_priority = None
        self._raises_delivered = 0
        self._child_handle = None

    async def _plan_and_start(self) -> bool:
        """Plan once and start a run if anything is planned; True ends the workflow."""
        self._planning = True
        try:
            return await self._plan_and_start_once()
        finally:
            self._planning = False

    async def _plan_and_start_once(self) -> bool:
        manual = self._pending_manual
        manual_priority = self._pending_manual_priority
        reconciliation_id, run_id = self._mint_ids()
        now = workflow.now()
        self._take_commit_window()
        reasons, self._wake_reasons = self._wake_reasons, {}
        self._woken = False
        try:
            plan = await workflow.execute_activity(
                TableReconciliationActivity.PLAN_TABLE_MAINTENANCE,
                {
                    "table_uuid": self._table_uuid,
                    "now": now.isoformat(),
                    "manual_operations": manual or None,
                    "manual_priority": manual_priority if manual is not None else None,
                },
                start_to_close_timeout=_ACTIVITY_TIMEOUT,
                retry_policy=_ACTIVITY_RETRY,
            )
        except ActivityError as error:
            if is_cancelled_exception(error):
                raise asyncio.CancelledError from error
            workflow.logger.error("planning table %s failed: %s", self._table_uuid, error)
            self._consume_manual(manual, "the plan failed")
            self._next_plan_at = workflow.now() + self._interval
            return False
        self._follow_plan_triggers(plan)
        self._next_plan_at = workflow.now() + self._interval
        self._tag_table_name(plan["table_name"])
        record = {"reconciliation_id": reconciliation_id, "reconciled_at": now.isoformat(), "wake_reasons": reasons}
        if self._stopping:
            if plan["status"] != "skip" and plan["operations"]:
                self._drop_unstarted_plan(manual, reconciliation_id)
            else:
                self._consume_manual(manual, "the workflow is stopping")
                await self._record(record, plan, run_id=None, run_start_failed=False)
            return False
        if plan["status"] == "skip":
            self._consume_manual(manual, f"the table is skipped ({plan['reason']})")
            await self._record(record, plan, run_id=None, run_start_failed=False)
            return plan["reason"] in _ENDING_REASONS
        if not plan["operations"]:
            self._consume_manual(manual, "nothing was planned")
            await self._record(record, plan, run_id=None, run_start_failed=False)
            return False
        await self._await_closing()
        if self._stopping:
            self._drop_unstarted_plan(manual, reconciliation_id)
            return False
        started = await self._start_run(plan, manual is not None, run_id)
        if started:
            self._consume_manual(manual, None)
        elif manual is not None:
            workflow.logger.info("keeping manual trigger %s: its run did not start", manual)
        await self._record(record, plan, run_id=run_id if started else None, run_start_failed=not started)
        return False

    def _follow_plan_triggers(self, plan: dict[str, Any]) -> None:
        """Take the schedule interval and the commit debounce from the plan.

        A plan an older worker returned, as a history from before the debounce holds, names its
        interval ``reconcile_interval_seconds`` and has no debounce: its interval is read under that
        name, so the history replays, and the debounce stays the last one (it changes only what the
        activity returns, so it needs no patch).
        """
        interval = plan.get("schedule_interval_seconds", plan.get(_OLDER_PLAN_INTERVAL_KEY))
        if interval is not None:
            self._interval = timedelta(seconds=interval)
        if "catalog_commit_debounce_seconds" in plan:
            self._commit_debounce = _seconds_or_none(plan["catalog_commit_debounce_seconds"])

    @staticmethod
    def _mint_ids() -> tuple[str, str]:
        """Return a new reconciliation id and run id; a history from before prefixed ids replays its UUIDs."""
        if not workflow.patched(_PREFIXED_IDS_PATCH):
            return str(workflow.uuid4()), str(workflow.uuid4())
        return mint_workflow_prefixed_id(_RECONCILIATION_ID_PREFIX), mint_workflow_prefixed_id(_RUN_ID_PREFIX)

    async def _record(
        self, record: dict[str, Any], plan: dict[str, Any], *, run_id: str | None, run_start_failed: bool
    ) -> None:
        """Store one reconciliation of a table the plan found; a failure is logged and the loop goes on.

        The record points at the plan's policy by id and carries the plan's ``policy_name`` for
        display. A plan an older worker returned names its policy instead and has no ``policy_id``
        (or no ``policy_name``): the record then carries none, the recorder refuses it and the
        refusal is logged like any other failure (it changes only the activity's input, so it
        needs no patch).
        """
        if not plan["table_found"]:
            return
        try:
            await workflow.execute_activity(
                TableReconciliationActivity.RECORD_TABLE_RECONCILIATION,
                {
                    **record,
                    "table_uuid": self._table_uuid,
                    "dry_run": plan["dry_run"],
                    "status": plan["status"],
                    "skip_reason": plan["reason"],
                    "checks": plan["checks"],
                    "run_id": run_id,
                    "run_start_failed": run_start_failed,
                    "policy_id": plan.get("policy_id"),
                    "policy_name": plan.get("policy_name"),
                    "policy_version": plan["policy_version"],
                    "policy_target": plan["policy_target"],
                },
                start_to_close_timeout=_ACTIVITY_TIMEOUT,
                retry_policy=_ACTIVITY_RETRY,
            )
        except ActivityError as error:
            if is_cancelled_exception(error):
                raise asyncio.CancelledError from error
            workflow.logger.error("recording reconciliation %s failed: %s", record["reconciliation_id"], error)

    def _drop_unstarted_plan(self, manual: list[str] | None, reconciliation_id: str) -> None:
        """Drop a plan with operations that is not started because the workflow is stopping, unrecorded."""
        self._consume_manual(manual, "the workflow is stopping")
        workflow.logger.info("not recording reconciliation %s: the workflow is stopping", reconciliation_id)

    def _consume_manual(self, manual: list[str] | None, dropped_because: str | None) -> None:
        if manual is None or self._pending_manual is not manual:
            return
        self._pending_manual = None
        self._pending_manual_priority = None
        if dropped_because is not None:
            workflow.logger.info("dropping manual trigger %s: %s", manual, dropped_because)

    async def _start_run(self, plan: dict[str, Any], manual: bool, run_id: str) -> bool:
        """Start the child run under ``run_id``; False when it could not be started.

        The child runs under the table's one maintenance workflow id: a run of the
        table still running refuses the start, and a closed one frees the id, so the
        caller first awaits the run that reported last until it closed (``_await_closing``).
        """
        child_id = table_maintenance_workflow_id(self._table_uuid)
        attempt_deadline_seconds = plan.get("attempt_deadline_seconds", DEFAULT_ATTEMPT_DEADLINE_SECONDS)
        max_attempts = plan.get("max_attempts", DEFAULT_MAX_ATTEMPTS)
        queue_wait_limit_seconds = plan.get("queue_wait_limit_seconds", DEFAULT_QUEUE_WAIT_LIMIT_SECONDS)
        self._in_flight_run_id = run_id
        self._in_flight_workflow_id = child_id
        self._in_flight_started_at = workflow.now()
        self._in_flight_operations = len(plan["operations"])
        self._in_flight_attempt_deadline_seconds = attempt_deadline_seconds
        self._in_flight_max_attempts = max_attempts
        self._in_flight_queue_wait_limit_seconds = queue_wait_limit_seconds
        trigger = _TRIGGER_MANUAL if manual else _TRIGGER_SCHEDULED
        operations = [op["operation"] for op in plan["operations"]]
        try:
            child = await workflow.start_child_workflow(
                TABLE_MAINTENANCE_WORKFLOW,
                TableMaintenanceWorkflowInput(
                    run_id=run_id,
                    table_uuid=self._table_uuid,
                    parent_workflow_id=workflow.info().workflow_id,
                    trigger=trigger,
                    plan=plan,
                    attempt_deadline_seconds=attempt_deadline_seconds,
                    max_attempts=max_attempts,
                    queue_wait_limit_seconds=queue_wait_limit_seconds,
                ),
                id=child_id,
                id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
                task_queue=TASK_QUEUE,
                parent_close_policy=ParentClosePolicy.ABANDON,
                static_summary=table_maintenance_summary(plan["table_name"], operations),
                search_attributes=self._run_search_attributes(plan["table_name"], operations, trigger),
            )
            child.add_done_callback(_discard_outcome)
            self._child_handle = child
        except FailureError as error:
            if is_cancelled_exception(error):
                raise asyncio.CancelledError from error
            workflow.logger.error(
                "starting maintenance run %s failed: %s; next plan at %s",
                run_id,
                error,
                _iso(self._next_plan_at),
            )
            self._clear_in_flight()
            return False
        return True

    def _run_search_attributes(
        self, table_name: str, operations: list[str], trigger: str
    ) -> TypedSearchAttributes | None:
        """Return the tags a new run starts with; none in a run from before the tags existed."""
        if not self._tags_table():
            return None
        keys = TableSearchAttributeKeys
        return TypedSearchAttributes(
            [
                SearchAttributePair(keys.TABLE_UUID, self._table_uuid),
                SearchAttributePair(keys.TABLE_NAME, table_name),
                SearchAttributePair(keys.MAINTENANCE_OPERATIONS, operations),
                SearchAttributePair(keys.MAINTENANCE_TRIGGER, trigger),
            ]
        )


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _seconds_or_none(seconds: int | None) -> timedelta | None:
    return None if seconds is None else timedelta(seconds=seconds)


def _whole_seconds_or_none(value: timedelta | None) -> int | None:
    return None if value is None else int(value.total_seconds())


def _earliest(*moments: datetime | None) -> datetime | None:
    """Return the earliest of the moments that are set, or ``None`` when none is."""
    return min((m for m in moments if m is not None), default=None)


def _discard_outcome(child: asyncio.Future[Any]) -> None:
    """Retrieve a child's outcome; a run reports only through ``maintenance_finished``."""
    if not child.cancelled():
        child.exception()
