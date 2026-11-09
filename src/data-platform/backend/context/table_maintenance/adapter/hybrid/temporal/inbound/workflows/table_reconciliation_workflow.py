"""Define the TableReconciliationWorkflow."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, FailureError, is_cancelled_exception
from temporalio.workflow import ParentClosePolicy

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    TABLE_MAINTENANCE_WORKFLOW,
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
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows.table_maintenance_attempt_policy import (
    TableMaintenanceAttemptPolicy,
)

_ACTIVITY_TIMEOUT = timedelta(minutes=2)
_ACTIVITY_RETRY = RetryPolicy(maximum_attempts=5, initial_interval=timedelta(seconds=2), backoff_coefficient=2.0)
_IN_FLIGHT_PER_OPERATION = TableMaintenanceAttemptPolicy().operation_worst_case() + timedelta(hours=1)
_CANCEL_GRACE = timedelta(minutes=15)
_ENDING_REASONS = frozenset({"dropped", "excluded"})
_TRIGGER_SCHEDULED = "scheduled"
_TRIGGER_MANUAL = "manual"
_REASON_SCHEDULE = "schedule"
_REASON_CATALOG_COMMIT = "catalog_commit"
_REASON_SETTINGS_CHANGED = "settings_changed"
_REASON_RESUMED = "resumed"
_REASON_PAUSED = "paused"
_REASON_MANUAL_RUN = "manual_run"
_REASON_RECONCILE_NOW = "reconcile_now"
_REASON_PREVIOUS_RUN_FINISHED = "previous_run_finished"


@workflow.defn(name=TABLE_RECONCILIATION_WORKFLOW)
class TableReconciliationWorkflow:
    """Plan and start the maintenance runs of one table, one run at a time.

    The loop wakes on its timer (the table's reconcile interval, from the last
    plan; one hour at first) or on any signal, and then asks
    ``plan_table_maintenance``, which reloads the table: the database is the
    authority on pause, resume and settings, so those signals only wake the loop.
    A non-empty plan starts a ``TableMaintenanceWorkflow`` child that outlives this run
    (``ABANDON``) and reports back only through ``maintenance_finished``, which is
    why the run in flight survives continue-as-new. While a run is in flight
    nothing is planned; a ``trigger_now`` is kept and planned once it finishes. A
    run that never reports back is given up once the child's worst case has passed
    (per planned operation: every attempt timing out, plus the backoffs, plus 1 h):
    the child is cancelled first (by the workflow ID recorded when it started, as
    the ID carries the table name of that time), so its cleanup records the
    result, releases its admission slot and deletes its Spark job, and its report
    is awaited for up to 15 minutes (less if the cancel fails because the child
    is gone or no workflow ID was recorded), so a new
    run does not overlap the old one's Spark job. A skip
    because the table was dropped or excluded, or a
    ``stop`` signal, ends the workflow once no run is in flight, but never on a
    stale decision (R31): any other signal after ``stop`` cancels the stop, and a
    wake that arrives while a plan says dropped or excluded makes it plan again.

    Every wake also counts its reason (the timer counts ``schedule``; ``stop``
    counts nothing). The reasons accumulate, through runs in flight and
    continue-as-new, until the next plan takes them; reasons that arrive while
    a plan is running belong to the plan they wake next. After each plan that
    found the table, ``record_table_reconciliation`` stores the reconciliation
    with those reasons, the plan's checks and the run it started (or that its
    start failed). The run id is generated with the reconciliation id before
    planning, so the record and the run agree. A failed plan records nothing
    and drops its reasons; a failed record is logged and the loop goes on. A
    plan with operations that is not started because the workflow is stopping
    is not recorded either, since its due operations neither started nor
    failed to start.
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
        self._pending_manual = None if input.pending_manual is None else list(input.pending_manual)
        self._next_plan_at = datetime.fromisoformat(input.next_plan_at) if input.next_plan_at else None
        self._continue_as_new_after = input.continue_as_new_after
        self._interval = timedelta(seconds=input.reconcile_interval_seconds)
        self._wake_reasons: dict[str, int] = dict(input.wake_reasons or {})
        self._woken = False
        self._stopping = False
        self._planning = False
        self._signals_handled = 0
        self._cancel_failed = False
        self._cancel_task: asyncio.Task[None] | None = None

    @workflow.run
    async def run(self, input: TableReconciliationWorkflowInput) -> None:  # noqa: A002
        """Wait, plan and start runs until the table leaves maintenance."""
        if self._next_plan_at is None:
            self._next_plan_at = workflow.now() + self._interval
        iterations = 0
        while True:
            if self._stopping and self._in_flight_run_id is None:
                return
            if self._should_continue_as_new(iterations):
                await workflow.wait_condition(workflow.all_handlers_finished)
                if not self._woken:
                    workflow.continue_as_new(self._carry())
            await self._wait()
            self._woken = False
            iterations += 1
            if self._in_flight_run_id is not None:
                await self._give_up_stuck_run()
            if self._in_flight_run_id is None and not self._stopping:
                ends = await self._plan_and_start()
                if ends and not self._woken:
                    return

    @workflow.signal(name=TableReconciliationSignal.SETTINGS_CHANGED)
    def settings_changed(self, payload: dict | None = None) -> None:
        """Wake the loop to re-plan with the settings stored in the database."""
        self._wake(_REASON_SETTINGS_CHANGED, cancels_stop=True)

    @workflow.signal(name=TableReconciliationSignal.TABLE_UPDATED)
    def table_updated(self, payload: dict | None = None) -> None:
        """Wake the loop because the table changed in the catalog."""
        self._wake(_REASON_CATALOG_COMMIT, cancels_stop=True)

    @workflow.signal(name=TableReconciliationSignal.PAUSE)
    def pause(self, payload: dict | None = None) -> None:
        """Wake the loop; the plan sees the paused table and skips."""
        self._wake(_REASON_PAUSED, cancels_stop=True)

    @workflow.signal(name=TableReconciliationSignal.RESUME)
    def resume(self, payload: dict | None = None) -> None:
        """Wake the loop; the plan sees the resumed table and plans again."""
        self._wake(_REASON_RESUMED, cancels_stop=True)

    @workflow.signal(name=TableReconciliationSignal.TRIGGER_NOW)
    def trigger_now(self, payload: dict | None = None) -> None:
        """Keep a manual trigger, replacing any pending one, and wake the loop."""
        operations = (payload or {}).get("operations") or []
        self._pending_manual = [str(op) for op in operations]
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
        self._clear_in_flight()
        self._count(_REASON_PREVIOUS_RUN_FINISHED)
        self._woken = True

    @workflow.query
    def state(self) -> dict[str, Any]:
        """Report the run in flight, the pending manual trigger, the timer, the wake reasons and the loop."""
        return {
            "in_flight_run_id": self._in_flight_run_id,
            "in_flight_workflow_id": self._in_flight_workflow_id,
            "in_flight_started_at": _iso(self._in_flight_started_at),
            "pending_manual": self._pending_manual,
            "stopping": self._stopping,
            "next_plan_at": _iso(self._next_plan_at),
            "reconcile_interval_seconds": int(self._interval.total_seconds()),
            "woken": self._woken,
            "wake_reasons": dict(self._wake_reasons),
            "planning": self._planning,
            "signals_handled": self._signals_handled,
        }

    def _wake(self, reason: str | None, *, cancels_stop: bool) -> None:
        """Wake the loop and count the reason; a decision signal after ``stop`` supersedes it (R31)."""
        self._signals_handled += 1
        if cancels_stop:
            self._stopping = False
        if reason is not None:
            self._count(reason)
        self._woken = True

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
            next_plan_at=_iso(self._next_plan_at),
            reconcile_interval_seconds=int(self._interval.total_seconds()),
            continue_as_new_after=self._continue_as_new_after,
            wake_reasons=dict(self._wake_reasons),
        )

    async def _wait(self) -> None:
        wake_at = self._in_flight_deadline() or self._next_plan_at
        timeout = None if wake_at is None else wake_at - workflow.now()
        if timeout is not None and timeout <= timedelta(0):
            self._count(_REASON_SCHEDULE)
            return
        try:
            await workflow.wait_condition(lambda: self._woken, timeout=timeout)
        except TimeoutError:
            self._count(_REASON_SCHEDULE)

    def _in_flight_deadline(self) -> datetime | None:
        if self._in_flight_run_id is None or self._in_flight_started_at is None:
            return None
        started_at = self._in_flight_started_at
        return started_at + _IN_FLIGHT_PER_OPERATION * max(self._in_flight_operations, 1)

    async def _give_up_stuck_run(self) -> None:
        """Cancel a run past its budget, await its report briefly, then forget it.

        The cancel request runs as its own task: a request the server never
        resolves must not block the loop, and a failed one (the child is missing
        or closed, so nothing can report back) ends the wait at once.
        """
        deadline = self._in_flight_deadline()
        run_id = self._in_flight_run_id
        if run_id is None or deadline is None or workflow.now() < deadline:
            return
        workflow.logger.warning("maintenance run %s never reported back; cancelling it", run_id)
        self._cancel_failed = False
        self._cancel_task = asyncio.create_task(self._cancel_child(run_id, self._in_flight_workflow_id))
        try:
            await workflow.wait_condition(
                lambda: self._in_flight_run_id != run_id or self._cancel_failed,
                timeout=_CANCEL_GRACE,
            )
        except TimeoutError:
            workflow.logger.warning("cancelled run %s did not report back; no longer waiting", run_id)
        if self._in_flight_run_id == run_id:
            self._clear_in_flight()

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

    def _clear_in_flight(self) -> None:
        self._in_flight_run_id = None
        self._in_flight_workflow_id = None
        self._in_flight_started_at = None
        self._in_flight_operations = 0

    async def _plan_and_start(self) -> bool:
        """Plan once and start a run if anything is planned; True ends the workflow."""
        self._planning = True
        try:
            return await self._plan_and_start_once()
        finally:
            self._planning = False

    async def _plan_and_start_once(self) -> bool:
        manual = self._pending_manual
        reconciliation_id = str(workflow.uuid4())
        run_id = str(workflow.uuid4())
        now = workflow.now()
        reasons, self._wake_reasons = self._wake_reasons, {}
        try:
            plan = await workflow.execute_activity(
                TableReconciliationActivity.PLAN_TABLE_MAINTENANCE,
                {
                    "table_uuid": self._table_uuid,
                    "now": now.isoformat(),
                    "manual_operations": manual or None,
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
        self._interval = timedelta(seconds=plan["reconcile_interval_seconds"])
        self._next_plan_at = workflow.now() + self._interval
        record = {"reconciliation_id": reconciliation_id, "reconciled_at": now.isoformat(), "wake_reasons": reasons}
        if self._stopping:
            self._consume_manual(manual, "the workflow is stopping")
            if plan["status"] != "skip" and plan["operations"]:
                workflow.logger.info("not recording reconciliation %s: the workflow is stopping", reconciliation_id)
            else:
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
        self._consume_manual(manual, None)
        started = await self._start_run(plan, manual is not None, run_id)
        await self._record(record, plan, run_id=run_id if started else None, run_start_failed=not started)
        return False

    async def _record(
        self, record: dict[str, Any], plan: dict[str, Any], *, run_id: str | None, run_start_failed: bool
    ) -> None:
        """Store one reconciliation of a table the plan found; a failure is logged and the loop goes on."""
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
                },
                start_to_close_timeout=_ACTIVITY_TIMEOUT,
                retry_policy=_ACTIVITY_RETRY,
            )
        except ActivityError as error:
            if is_cancelled_exception(error):
                raise asyncio.CancelledError from error
            workflow.logger.error("recording reconciliation %s failed: %s", record["reconciliation_id"], error)

    def _consume_manual(self, manual: list[str] | None, dropped_because: str | None) -> None:
        if manual is None or self._pending_manual is not manual:
            return
        self._pending_manual = None
        if dropped_because is not None:
            workflow.logger.info("dropping manual trigger %s: %s", manual, dropped_because)

    async def _start_run(self, plan: dict[str, Any], manual: bool, run_id: str) -> bool:
        """Start the child run under ``run_id``; False when it could not be started."""
        child_id = table_maintenance_workflow_id(plan["table_name"], run_id)
        self._in_flight_run_id = run_id
        self._in_flight_workflow_id = child_id
        self._in_flight_started_at = workflow.now()
        self._in_flight_operations = len(plan["operations"])
        try:
            child = await workflow.start_child_workflow(
                TABLE_MAINTENANCE_WORKFLOW,
                TableMaintenanceWorkflowInput(
                    run_id=run_id,
                    table_uuid=self._table_uuid,
                    parent_workflow_id=workflow.info().workflow_id,
                    trigger=_TRIGGER_MANUAL if manual else _TRIGGER_SCHEDULED,
                    plan=plan,
                ),
                id=child_id,
                task_queue=TASK_QUEUE,
                parent_close_policy=ParentClosePolicy.ABANDON,
                static_summary=table_maintenance_summary(
                    plan["table_name"], [op["operation"] for op in plan["operations"]]
                ),
            )
            child.add_done_callback(_discard_outcome)
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


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _discard_outcome(child: asyncio.Future[Any]) -> None:
    """Retrieve a child's outcome; a run reports only through ``maintenance_finished``."""
    if not child.cancelled():
        child.exception()
