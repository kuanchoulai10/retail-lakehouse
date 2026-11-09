"""Test the TableReconciliationWorkflow on a time-skipping Temporal test server."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from temporalio.client import WorkflowExecutionStatus
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import UnsandboxedWorkflowRunner, Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    table_maintenance_workflow_id,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TABLE_RECONCILIATION_WORKFLOW,
    TableReconciliationSignal,
    TableReconciliationWorkflowInput,
    table_reconciliation_workflow_id,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import (
    TableReconciliationWorkflow,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.eventually import (
    eventually,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.scripted_plan_activity import (
    ScriptedPlanActivity,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.scripted_record_activity import (
    ScriptedRecordActivity,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.table_maintenance_stub_workflow import (
    TableMaintenanceStubWorkflow,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    import pytest
    from temporalio.client import Client, WorkflowHandle
    from temporalio.worker import WorkflowRunner

UUID = "u1"
TABLE = "iceberg.e2e.t"
WORKFLOW_ID = table_reconciliation_workflow_id(UUID)
COMPACTION = "rewrite_data_files"
EXPIRE = "expire_snapshots"
REAL_TIMEOUT_SECONDS = 20


def _check(operation: str, verdict: str = "due") -> dict[str, Any]:
    return {
        "operation": operation,
        "verdict": verdict,
        "combine": "all",
        "measurements": [],
        "next_eligible_at": None,
    }


def _planned(*operations: str, interval: int = 3600) -> dict[str, Any]:
    return {
        "status": "planned",
        "reason": None,
        "reconcile_interval_seconds": interval,
        "table_name": TABLE,
        "operations": [{"operation": op, "filters": [], "procedure_args": {}} for op in operations],
        "dry_run": False,
        "table_found": True,
        "checks": [_check(op) for op in operations],
    }


def _dry_run(*due: str) -> dict[str, Any]:
    return {**_planned(), "dry_run": True, "checks": [_check(op) for op in due]}


def _skip(reason: str, interval: int = 3600, *, table_found: bool = True) -> dict[str, Any]:
    return {
        "status": "skip",
        "reason": reason,
        "reconcile_interval_seconds": interval,
        "table_name": TABLE if table_found else None,
        "operations": [],
        "dry_run": False,
        "table_found": table_found,
        "checks": [],
    }


def _child_id(run_id: str) -> str:
    return table_maintenance_workflow_id(TABLE, run_id)


def _within_a_second(gap: timedelta, seconds: int) -> bool:
    """Tell whether ``gap`` is ``seconds`` long, allowing for the activity's run time."""
    return timedelta(seconds=seconds) <= gap < timedelta(seconds=seconds + 1)


@dataclass
class Harness:
    """Run the reconciliation workflow against a scripted plan activity and stub children."""

    env: WorkflowEnvironment
    client: Client
    plans: ScriptedPlanActivity
    recorder: ScriptedRecordActivity
    handle: WorkflowHandle | None = None
    sent: int = 0

    async def start(self, start_signal: str | None = TableReconciliationSignal.RESUME, **fields: Any) -> WorkflowHandle:
        """Start the workflow with a start signal and the given input fields."""
        options: dict[str, Any] = {}
        if start_signal is not None:
            options = {"start_signal": start_signal, "start_signal_args": [{}]}
            self.sent += 1
        self.handle = await self.client.start_workflow(
            TABLE_RECONCILIATION_WORKFLOW,
            TableReconciliationWorkflowInput(table_uuid=UUID, **fields),
            id=WORKFLOW_ID,
            task_queue=TASK_QUEUE,
            **options,
        )
        return self.handle

    async def signal(self, name: str, payload: dict | None = None) -> None:
        """Send a signal with an optional payload to the workflow."""
        handle = self.client.get_workflow_handle(WORKFLOW_ID)
        self.sent += 1
        if payload is None:
            await handle.signal(name)
        else:
            await handle.signal(name, payload)

    async def state(self) -> dict[str, Any]:
        """Query the state of the workflow."""
        return await self.client.get_workflow_handle(WORKFLOW_ID).query("state")

    async def plan_count(self, count: int) -> list[dict[str, Any]]:
        """Wait until at least the given number of plans were requested and return the requests."""

        async def probe() -> list[dict[str, Any]]:
            return list(self.plans.requests)

        return await eventually(probe, lambda r: len(r) >= count)

    async def records(self, count: int) -> list[dict[str, Any]]:
        """Wait until at least the given number of reconciliations were recorded and return them."""

        async def probe() -> list[dict[str, Any]]:
            return list(self.recorder.records)

        return await eventually(probe, lambda r: len(r) >= count)

    async def in_flight(self) -> str:
        """Return the run id of the in-flight maintenance run."""
        state = await eventually(self.state, lambda s: s["in_flight_run_id"])
        return state["in_flight_run_id"]

    async def idle_after(self, before: dict[str, Any]) -> dict[str, Any]:
        """Wait until the carried in-flight run of ``before`` is no longer tracked."""
        return await eventually(
            self.state,
            lambda s: s["in_flight_run_id"] != before["in_flight_run_id"] and not s["planning"],
        )

    async def child(self, run_id: str) -> dict[str, Any]:
        """Query the stub child of a run for the input it started with."""
        handle = self.client.get_workflow_handle(_child_id(run_id))
        return await handle.query("started_with")

    async def child_summary(self, run_id: str) -> str | None:
        """Return the static summary of the child workflow of a run."""
        handle = self.client.get_workflow_handle(_child_id(run_id))
        return await (await handle.describe()).static_summary()

    async def child_status(self, run_id: str) -> WorkflowExecutionStatus | None:
        """Return the execution status of the child workflow of a run."""
        handle = self.client.get_workflow_handle(_child_id(run_id))
        return (await handle.describe()).status

    async def complete_child(self, run_id: str) -> None:
        """Signal the stub child of a run to finish."""
        handle = self.client.get_workflow_handle(_child_id(run_id))
        await handle.signal("complete")
        self.sent += 1

    async def ended(self) -> None:
        """Wait until the workflow has ended."""
        handle = self.client.get_workflow_handle(WORKFLOW_ID)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

    async def status(self) -> WorkflowExecutionStatus | None:
        """Return the execution status of the workflow."""
        handle = self.client.get_workflow_handle(WORKFLOW_ID)
        return (await handle.describe()).status

    async def settle(self) -> dict[str, Any]:
        """Wait until every signal sent was handled and the loop is idle again.

        Signal handlers and the loop iteration they wake run in one workflow
        activation, so a query seeing all signals handled, no wake pending and no
        plan running proves the loop has reacted to everything that was sent.
        """
        return await eventually(
            self.state,
            lambda s: s["signals_handled"] >= self.sent and not s["woken"] and not s["planning"],
        )


def _run(
    scenario: Callable[[Harness], Awaitable[None]],
    script: Callable[[dict[str, Any]], dict[str, Any]] = lambda _: _planned(),
    runner: WorkflowRunner | None = None,
) -> None:
    async def go() -> None:
        async with await WorkflowEnvironment.start_time_skipping() as env:
            plans = ScriptedPlanActivity(script)
            recorder = ScriptedRecordActivity()
            async with Worker(
                env.client,
                task_queue=TASK_QUEUE,
                workflows=[TableReconciliationWorkflow, TableMaintenanceStubWorkflow],
                activities=[plans.plan_table_maintenance, recorder.record_table_reconciliation],
                workflow_runner=runner or SandboxedWorkflowRunner(),
            ):
                await scenario(Harness(env, env.client, plans, recorder))

    asyncio.run(go())


def test_timer_triggers_plan_every_interval():
    """Without a start signal the workflow plans only when its timer fires, then waits one planned interval."""

    async def scenario(h: Harness) -> None:
        await h.start(start_signal=None)
        started = await eventually(h.state, lambda s: s["next_plan_at"] is not None)
        await h.env.sleep(timedelta(seconds=3500))
        assert (await h.settle())["next_plan_at"] == started["next_plan_at"]
        assert h.plans.requests == []
        await h.env.sleep(timedelta(seconds=200))
        first = (await h.plan_count(1))[0]
        assert first["table_uuid"] == UUID
        assert first["manual_operations"] is None
        after_first = await h.settle()
        due = datetime.fromisoformat(after_first["next_plan_at"])
        assert _within_a_second(due - datetime.fromisoformat(first["now"]), 1800)
        await h.env.sleep(timedelta(seconds=1500))
        assert (await h.settle())["next_plan_at"] == after_first["next_plan_at"]
        assert len(h.plans.requests) == 1
        await h.env.sleep(timedelta(seconds=400))
        second = (await h.plan_count(2))[1]
        gap = datetime.fromisoformat(second["now"]) - datetime.fromisoformat(first["now"])
        assert timedelta(seconds=1800) <= gap < timedelta(seconds=1900)

    _run(scenario, script=lambda _: _planned(interval=1800))


def test_signal_with_start_plans_and_starts_child_with_abandon_semantics():
    """A start signal plans and starts a scheduled child run that outlives the parent."""

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        child = await h.child(run_id)
        assert child["table_uuid"] == UUID
        assert child["parent_workflow_id"] == WORKFLOW_ID
        assert child["trigger"] == "scheduled"
        assert child["plan"] == _planned(COMPACTION)
        assert len(h.plans.requests) == 1
        assert (await h.state())["in_flight_workflow_id"] == (f"table-maintenance:table={TABLE}:run={run_id}")

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_child_summary_names_the_table_and_the_planned_operations():
    """The child workflow summary names the table and the planned operations."""

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        assert await h.child_summary(run_id) == (f"{TABLE} · {COMPACTION}, {EXPIRE}")

    _run(scenario, script=lambda _: _planned(COMPACTION, EXPIRE))


def test_trigger_now_while_in_flight_runs_after_finish():
    """A manual trigger during a run is kept and planned after the run finishes."""

    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.signal(TableReconciliationSignal.TRIGGER_NOW, {"operations": [COMPACTION]})
        await h.signal(TableReconciliationSignal.TRIGGER_NOW, {"operations": [EXPIRE]})
        await h.settle()
        assert len(h.plans.requests) == 1
        assert (await h.state())["pending_manual"] == [EXPIRE]
        await h.complete_child(first)
        second_plan = (await h.plan_count(2))[1]
        assert second_plan["manual_operations"] == [EXPIRE]
        second = await eventually(h.state, lambda s: s["in_flight_run_id"] not in (None, first))
        assert second["pending_manual"] is None
        child = await h.child(second["in_flight_run_id"])
        assert child["trigger"] == "manual"

    _run(scenario, script=lambda r: _planned(*(r["manual_operations"] or [COMPACTION])))


def test_trigger_now_without_operations_plans_all_due_as_manual():
    """A manual trigger without operations plans every due operation as a manual run."""

    async def scenario(h: Harness) -> None:
        await h.start(start_signal=TableReconciliationSignal.TRIGGER_NOW)
        run_id = await h.in_flight()
        assert h.plans.requests[0]["manual_operations"] is None
        assert (await h.child(run_id))["trigger"] == "manual"
        record = (await h.records(1))[0]
        assert record["wake_reasons"] == {"manual_run": 1}
        assert record["run_id"] == run_id

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_child_result_received_after_continue_as_new():
    """A child result that arrives after continue as new still finishes the in-flight run."""

    async def scenario(h: Harness) -> None:
        handle = await h.start(continue_as_new_after=2)
        first_run = handle.result_run_id
        run_id = await h.in_flight()
        await h.signal(TableReconciliationSignal.TRIGGER_NOW, {"operations": [EXPIRE]})
        for _ in range(3):
            await h.signal(TableReconciliationSignal.SETTINGS_CHANGED)

        async def run_id_now() -> str | None:
            return (await h.client.get_workflow_handle(WORKFLOW_ID).describe()).run_id

        await eventually(run_id_now, lambda r: r != first_run)
        state = await h.state()
        assert state["in_flight_run_id"] == run_id
        assert state["in_flight_workflow_id"] == _child_id(run_id)
        assert state["pending_manual"] == [EXPIRE]
        assert len(h.plans.requests) == 1
        await h.complete_child(run_id)
        second_plan = (await h.plan_count(2))[1]
        assert second_plan["manual_operations"] == [EXPIRE]

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_stale_maintenance_finished_is_ignored():
    """A finished signal for a run that is not in flight is ignored."""

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        await h.signal(
            TableReconciliationSignal.MAINTENANCE_FINISHED,
            {"run_id": "other", "record_failures": 0},
        )
        await h.settle()
        assert (await h.state())["in_flight_run_id"] == run_id
        assert len(h.plans.requests) == 1

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_dropped_signal_ends_workflow_after_in_flight_run():
    """A dropped signal stops the workflow only after the in-flight run finishes."""

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        await h.signal(TableReconciliationSignal.STOP)
        state = await h.settle()
        assert state["stopping"] is True
        assert state["in_flight_run_id"] == run_id
        assert await h.status() == WorkflowExecutionStatus.RUNNING
        await h.complete_child(run_id)
        await h.ended()
        assert len(h.plans.requests) == 1

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_stop_with_nothing_in_flight_ends_immediately():
    """A stop with no run in flight ends the workflow at once."""

    async def scenario(h: Harness) -> None:
        await h.start(start_signal=None)
        await h.signal(TableReconciliationSignal.STOP)
        await h.ended()
        assert h.plans.requests == []

    _run(scenario)


def test_skip_excluded_ends_workflow():
    """A plan that skips an excluded table ends the workflow."""

    async def scenario(h: Harness) -> None:
        await h.start()
        await h.ended()
        assert len(h.plans.requests) == 1
        [record] = h.recorder.records
        assert record["status"] == "skip"
        assert record["skip_reason"] == "excluded"
        assert record["wake_reasons"] == {"resumed": 1}

    _run(scenario, script=lambda _: _skip("excluded"))


def test_skip_dropped_ends_workflow():
    """A plan that skips a dropped table ends the workflow."""

    async def scenario(h: Harness) -> None:
        await h.start()
        await h.ended()

    _run(scenario, script=lambda _: _skip("dropped"))


def test_pause_skips_plans_resume_restores():
    """Pausing makes plans skip and resuming restores planning."""
    paused = {"value": True}

    def script(_: dict[str, Any]) -> dict[str, Any]:
        return _skip("paused") if paused["value"] else _planned(COMPACTION)

    async def scenario(h: Harness) -> None:
        await h.start()
        await h.plan_count(1)
        await h.signal(TableReconciliationSignal.PAUSE)
        await h.plan_count(2)
        await h.settle()
        assert (await h.state())["in_flight_run_id"] is None
        assert await h.status() == WorkflowExecutionStatus.RUNNING
        paused["value"] = False
        await h.signal(TableReconciliationSignal.RESUME)
        run_id = await h.in_flight()
        assert (await h.child(run_id))["trigger"] == "scheduled"
        assert len(h.plans.requests) == 3

    _run(scenario, script=script)


def test_manual_trigger_on_paused_table_is_dropped():
    """A manual trigger on a paused table is planned once and then dropped."""
    paused = {"value": True}

    def script(_: dict[str, Any]) -> dict[str, Any]:
        return _skip("paused") if paused["value"] else _planned(COMPACTION)

    async def scenario(h: Harness) -> None:
        await h.start(start_signal=None)
        await h.signal(TableReconciliationSignal.TRIGGER_NOW, {"operations": [EXPIRE]})
        assert (await h.plan_count(1))[0]["manual_operations"] == [EXPIRE]
        await h.settle()
        assert (await h.state())["pending_manual"] is None
        paused["value"] = False
        await h.signal(TableReconciliationSignal.RESUME)
        assert (await h.plan_count(2))[1]["manual_operations"] is None
        run_id = await h.in_flight()
        assert (await h.child(run_id))["trigger"] == "scheduled"

    _run(scenario, script=script)


def test_plan_failure_does_not_fail_workflow():
    """A failing plan activity leaves the workflow running and retries after an hour."""

    async def scenario(h: Harness) -> None:
        h.plans.failures = 1
        await h.start()
        failed = (await h.plan_count(1))[0]
        state = await h.settle()
        assert state["in_flight_run_id"] is None
        due = datetime.fromisoformat(state["next_plan_at"])
        assert _within_a_second(due - datetime.fromisoformat(failed["now"]), 3600)
        assert await h.status() == WorkflowExecutionStatus.RUNNING
        assert state["wake_reasons"] == {}
        assert h.recorder.records == []
        await h.signal(TableReconciliationSignal.SETTINGS_CHANGED)
        await h.plan_count(2)
        await h.in_flight()
        assert (await h.records(1))[0]["wake_reasons"] == {"settings_changed": 1}

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_planned_empty_starts_no_child():
    """A plan with no operations starts no child run."""

    async def scenario(h: Harness) -> None:
        await h.start()
        await h.plan_count(1)
        state = await h.settle()
        assert state["in_flight_run_id"] is None
        assert len(h.plans.requests) == 1

    _run(scenario, script=lambda _: _planned())


# Per planned operation: 3 attempts of 6 h, backoffs of 60 s + 120 s, 1 h margin.
OPERATION_BUDGET = timedelta(hours=19, minutes=3)


def test_in_flight_run_is_given_up_only_after_the_child_worst_case():
    """An in-flight run is given up only after the child worst case time has passed."""

    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        started_at = (await h.state())["in_flight_started_at"]
        await h.env.sleep(2 * OPERATION_BUDGET - timedelta(minutes=1))
        state = await h.settle()
        assert state["in_flight_run_id"] == first
        assert state["in_flight_started_at"] == started_at
        assert len(h.plans.requests) == 1
        assert await h.child_status(first) == WorkflowExecutionStatus.RUNNING
        await h.env.sleep(timedelta(minutes=2))
        await h.plan_count(2)
        await eventually(h.state, lambda s: s["in_flight_run_id"] not in (None, first) and not s["planning"])
        # The cancelled child reports back, so the next plan wakes on its finish, not on schedule.
        assert [r["wake_reasons"] for r in h.recorder.records] == [{"resumed": 1}, {"previous_run_finished": 1}]

    _run(scenario, script=lambda _: _planned(COMPACTION, EXPIRE, interval=10**6))


def test_give_up_cancels_the_stale_child_before_starting_a_new_run():
    """Giving up a stale run cancels its child before the next run starts."""

    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.env.sleep(OPERATION_BUDGET + timedelta(minutes=1))
        await h.plan_count(2)
        second = (await eventually(h.state, lambda s: s["in_flight_run_id"] not in (None, first)))["in_flight_run_id"]
        assert await h.child_status(first) == WorkflowExecutionStatus.CANCELED
        assert await h.child_status(second) == WorkflowExecutionStatus.RUNNING

    _run(scenario, script=lambda _: _planned(COMPACTION, interval=10**6))


def test_give_up_waits_a_grace_for_a_child_that_ignores_its_cancel():
    """Giving up waits a grace period for a child that ignores its cancel."""
    plan = {**_planned(COMPACTION, interval=10**6), "stub_ignores_cancel": True}

    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.env.sleep(OPERATION_BUDGET + timedelta(minutes=14))
        state = await h.settle()
        assert state["in_flight_run_id"] == first
        assert len(h.plans.requests) == 1
        await h.env.sleep(timedelta(minutes=2))
        await h.plan_count(2)
        await eventually(h.state, lambda s: s["in_flight_run_id"] not in (None, first) and not s["planning"])
        await h.complete_child(first)
        await h.settle()
        assert len(h.plans.requests) == 2
        assert [r["wake_reasons"] for r in h.recorder.records] == [{"resumed": 1}, {"previous_run_finished": 1}]

    _run(scenario, script=lambda _: plan)


def test_include_after_exclude_while_in_flight_keeps_workflow():
    """Including a table again while a run is in flight keeps the workflow from stopping."""

    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.signal(TableReconciliationSignal.STOP)
        await h.signal(TableReconciliationSignal.RESUME)
        assert (await h.settle())["stopping"] is False
        await h.complete_child(first)
        await h.plan_count(2)
        await eventually(h.state, lambda s: s["in_flight_run_id"] not in (None, first))
        assert await h.status() == WorkflowExecutionStatus.RUNNING

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_excluded_plan_with_wake_during_activity_replans():
    """An excluded plan followed by a wake signal during the activity plans again."""
    answers = [_skip("excluded"), _planned(COMPACTION)]

    async def scenario(h: Harness) -> None:
        h.plans.gate = asyncio.Event()
        await h.start()
        await h.plan_count(1)
        await h.signal(TableReconciliationSignal.RESUME)
        await eventually(h.state, lambda s: s["signals_handled"] >= h.sent)
        h.plans.gate.set()
        await h.plan_count(2)
        await h.in_flight()
        assert await h.status() == WorkflowExecutionStatus.RUNNING

    _run(scenario, script=lambda _: answers.pop(0))


def test_stop_during_plan_starts_no_child():
    """A stop that arrives while planning starts no child run."""

    async def scenario(h: Harness) -> None:
        h.plans.gate = asyncio.Event()
        await h.start()
        await h.plan_count(1)
        await h.signal(TableReconciliationSignal.STOP)
        await eventually(h.state, lambda s: s["stopping"])
        h.plans.gate.set()
        await h.ended()
        assert len(h.plans.requests) == 1
        assert h.recorder.records == []

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_continue_as_new_carries_interval_used_after_plan_failure():
    """Continue as new keeps the retry interval used after a plan failure."""

    async def scenario(h: Harness) -> None:
        await h.start(continue_as_new_after=1)
        await h.plan_count(1)
        h.plans.failures = 1
        await h.env.sleep(timedelta(seconds=610))
        failed = (await h.plan_count(2))[1]
        await h.env.sleep(timedelta(seconds=610))
        third = (await h.plan_count(3))[2]
        gap = datetime.fromisoformat(third["now"]) - datetime.fromisoformat(failed["now"])
        assert timedelta(seconds=600) <= gap < timedelta(seconds=700)

    _run(scenario, script=lambda _: _planned(interval=600))


def test_carried_in_flight_run_without_start_time_gets_a_fixed_deadline():
    """A carried in-flight run without a start time gets a fixed deadline and blocks planning meanwhile."""

    async def scenario(h: Harness) -> None:
        await h.start(
            start_signal=None,
            in_flight_run_id="ghost",
            in_flight_workflow_id=_child_id("ghost"),
            in_flight_operation_count=1,
        )
        state = await eventually(h.state, lambda s: s["in_flight_started_at"])
        await h.env.sleep(OPERATION_BUDGET - timedelta(minutes=1))
        assert (await h.settle())["in_flight_run_id"] == "ghost"
        assert h.plans.requests == []
        # The time-skipping test server never resolves a cancel of a missing
        # workflow, so the give-up falls back to the 15 min grace here.
        await h.env.sleep(timedelta(minutes=17))
        await h.plan_count(1)
        await h.idle_after(state)

    _run(scenario, script=lambda _: _planned())


def test_carried_in_flight_run_without_workflow_id_is_given_up_without_grace():
    """A carried in-flight run without a workflow id is given up without a grace period."""

    async def scenario(h: Harness) -> None:
        await h.start(start_signal=None, in_flight_run_id="ghost", in_flight_operation_count=1)
        state = await eventually(h.state, lambda s: s["in_flight_started_at"])
        assert state["in_flight_workflow_id"] is None
        await h.env.sleep(OPERATION_BUDGET + timedelta(minutes=1))
        await h.plan_count(1)
        await h.idle_after(state)
        # The give-up ends the run, and the plan timer (one hour) came due while it was stuck.
        assert [r["wake_reasons"] for r in (await h.records(1))] == [{"previous_run_finished": 1, "schedule": 1}]

    _run(scenario, script=lambda _: _planned())


def test_child_start_failure_keeps_workflow_alive(monkeypatch: pytest.MonkeyPatch):
    """A failure to start the child run clears the in-flight run and keeps the workflow alive."""
    import temporalio.workflow

    real_start = temporalio.workflow.start_child_workflow
    answers = [_planned(COMPACTION), _planned(EXPIRE)]

    async def flaky_start(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        # Decided by the plan in history, so a replay takes the same path.
        if args[1].plan["operations"][0]["operation"] == COMPACTION:
            raise WorkflowAlreadyStartedError(kwargs["id"], args[0])
        return await real_start(*args, **kwargs)

    monkeypatch.setattr(temporalio.workflow, "start_child_workflow", flaky_start)

    async def scenario(h: Harness) -> None:
        await h.start()
        await h.plan_count(1)
        state = await h.settle()
        assert state["in_flight_run_id"] is None
        assert state["in_flight_started_at"] is None
        assert await h.status() == WorkflowExecutionStatus.RUNNING
        await h.signal(TableReconciliationSignal.SETTINGS_CHANGED)
        await h.plan_count(2)
        run_id = await h.in_flight()
        assert (await h.child(run_id))["plan"] == _planned(EXPIRE)

    _run(
        scenario,
        script=lambda _: answers.pop(0),
        runner=UnsandboxedWorkflowRunner(),
    )


# --- reconciliation records ---


def test_timer_wake_records_schedule():
    """A plan the timer woke is recorded with the schedule reason, the plan's time and its checks."""

    async def scenario(h: Harness) -> None:
        await h.start(start_signal=None)
        await h.env.sleep(timedelta(seconds=3700))
        plan = (await h.plan_count(1))[0]
        record = (await h.records(1))[0]
        assert record["reconciliation_id"]
        assert record["table_uuid"] == UUID
        assert record["reconciled_at"] == plan["now"]
        assert record["wake_reasons"] == {"schedule": 1}
        assert record["dry_run"] is False
        assert record["status"] == "planned"
        assert record["skip_reason"] is None
        assert record["checks"] == [_check(COMPACTION, "not_needed")]
        assert record["run_id"] is None
        assert record["run_start_failed"] is False

    _run(scenario, script=lambda _: {**_planned(), "checks": [_check(COMPACTION, "not_needed")]})


def test_three_catalog_commits_during_a_run_are_recorded_after_it_finishes():
    """Wakes that arrive while a run is in flight are kept and recorded by the plan after it finishes."""
    answers = [_planned(COMPACTION), _planned()]

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        first = (await h.records(1))[0]
        assert first["wake_reasons"] == {"resumed": 1}
        assert first["run_id"] == run_id
        assert (await h.child(run_id))["run_id"] == run_id
        for _ in range(3):
            await h.signal(TableReconciliationSignal.TABLE_UPDATED)
        state = await h.settle()
        assert state["wake_reasons"] == {"catalog_commit": 3}
        assert len(h.recorder.records) == 1
        await h.complete_child(run_id)
        second = (await h.records(2))[1]
        assert second["wake_reasons"] == {"catalog_commit": 3, "previous_run_finished": 1}
        assert second["reconciliation_id"] != first["reconciliation_id"]
        assert (await h.settle())["wake_reasons"] == {}

    _run(scenario, script=lambda _: answers.pop(0))


def test_reconcile_now_records_reconcile_now():
    """A reconcile now signal plans by the normal rules and records its reason."""

    async def scenario(h: Harness) -> None:
        await h.start(start_signal=None)
        await h.signal(TableReconciliationSignal.RECONCILE_NOW)
        assert (await h.plan_count(1))[0]["manual_operations"] is None
        run_id = await h.in_flight()
        assert (await h.child(run_id))["trigger"] == "scheduled"
        record = (await h.records(1))[0]
        assert record["wake_reasons"] == {"reconcile_now": 1}
        assert record["run_id"] == run_id

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_dry_run_plan_starts_nothing_and_records():
    """A dry run plan with a due operation starts no run and is recorded as a dry run."""

    async def scenario(h: Harness) -> None:
        await h.start()
        record = (await h.records(1))[0]
        state = await h.settle()
        assert state["in_flight_run_id"] is None
        assert record["dry_run"] is True
        assert record["checks"] == [_check(COMPACTION)]
        assert record["run_id"] is None
        assert record["run_start_failed"] is False

    _run(scenario, script=lambda _: _dry_run(COMPACTION))


def test_failed_child_start_records_start_failed(monkeypatch: pytest.MonkeyPatch):
    """A child that cannot be started is recorded as a failed start without a run id."""
    import temporalio.workflow

    async def failing_start(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        raise WorkflowAlreadyStartedError(kwargs["id"], args[0])

    monkeypatch.setattr(temporalio.workflow, "start_child_workflow", failing_start)

    async def scenario(h: Harness) -> None:
        await h.start()
        record = (await h.records(1))[0]
        assert (await h.settle())["in_flight_run_id"] is None
        assert record["run_id"] is None
        assert record["run_start_failed"] is True
        assert record["checks"] == [_check(COMPACTION)]

    _run(scenario, script=lambda _: _planned(COMPACTION), runner=UnsandboxedWorkflowRunner())


def test_missing_table_records_nothing():
    """A plan that finds no maintenance row for the table records nothing and ends the workflow."""

    async def scenario(h: Harness) -> None:
        await h.start()
        await h.ended()
        assert len(h.plans.requests) == 1
        assert h.recorder.records == []

    _run(scenario, script=lambda _: _skip("dropped", table_found=False))


def test_wake_reasons_survive_continue_as_new():
    """Wake reasons gathered while a run is in flight are carried through continue as new."""
    answers = [_planned(COMPACTION), _planned()]

    async def scenario(h: Harness) -> None:
        handle = await h.start(continue_as_new_after=2)
        first_run = handle.result_run_id
        run_id = await h.in_flight()
        for _ in range(3):
            await h.signal(TableReconciliationSignal.SETTINGS_CHANGED)

        async def run_id_now() -> str | None:
            return (await h.client.get_workflow_handle(WORKFLOW_ID).describe()).run_id

        await eventually(run_id_now, lambda r: r != first_run)
        assert (await h.state())["wake_reasons"] == {"settings_changed": 3}
        await h.complete_child(run_id)
        second = (await h.records(2))[1]
        assert second["wake_reasons"] == {"settings_changed": 3, "previous_run_finished": 1}

    _run(scenario, script=lambda _: answers.pop(0))


def test_failed_record_does_not_stop_the_loop():
    """A record that fails is logged; the run still starts and the next reconciliation is recorded."""
    answers = [_planned(COMPACTION), _planned()]

    async def scenario(h: Harness) -> None:
        h.recorder.failures = 1
        await h.start()
        run_id = await h.in_flight()
        await h.settle()
        assert h.recorder.records == []
        assert await h.status() == WorkflowExecutionStatus.RUNNING
        await h.complete_child(run_id)
        record = (await h.records(1))[0]
        assert record["wake_reasons"] == {"previous_run_finished": 1}

    _run(scenario, script=lambda _: answers.pop(0))


def test_reason_arriving_during_a_plan_goes_on_the_next_record():
    """A wake that arrives while a plan runs is recorded by the plan it causes, not the running one."""

    async def scenario(h: Harness) -> None:
        h.plans.gate = asyncio.Event()
        await h.start()
        await h.plan_count(1)
        await h.signal(TableReconciliationSignal.TABLE_UPDATED)
        await eventually(h.state, lambda s: s["signals_handled"] >= h.sent)
        h.plans.gate.set()
        first, second = (await h.records(2))[:2]
        assert first["wake_reasons"] == {"resumed": 1}
        assert second["wake_reasons"] == {"catalog_commit": 1}

    _run(scenario, script=lambda _: _planned())


def test_given_up_run_before_the_plan_timer_is_not_recorded_as_schedule():
    """Giving up a stuck run before the plan timer is due records only the wakes that arrived, not schedule."""
    answers = [_planned(COMPACTION, interval=10**6), _planned(interval=10**6)]

    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.signal(TableReconciliationSignal.TABLE_UPDATED)
        await h.env.sleep(OPERATION_BUDGET + timedelta(minutes=1))
        await h.plan_count(2)
        await eventually(h.state, lambda s: s["in_flight_run_id"] != first and not s["planning"])
        records = await h.records(2)
        assert [r["wake_reasons"] for r in records] == [
            {"resumed": 1},
            {"catalog_commit": 1, "previous_run_finished": 1},
        ]
        # The child's report during the grace ends the same run: no second count, no extra plan.
        await h.settle()
        assert len(h.plans.requests) == 2
        assert len(h.recorder.records) == 2

    _run(scenario, script=lambda _: answers.pop(0) if answers else _planned(interval=10**6))


def test_plan_timer_due_during_a_run_is_counted_once_it_finishes():
    """A plan tick that came due while a run was in flight is counted once, with the run's finish."""
    answers = [_planned(COMPACTION, interval=600), _planned(interval=600)]

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        await h.env.sleep(timedelta(seconds=1900))
        await h.settle()
        await h.complete_child(run_id)
        second = (await h.records(2))[1]
        assert second["wake_reasons"] == {"previous_run_finished": 1, "schedule": 1}

    _run(scenario, script=lambda _: answers.pop(0) if answers else _planned(interval=600))


def test_give_up_before_the_plan_timer_plans_once_as_previous_run_finished():
    """A stuck run given up before the plan timer ends the run: one plan, recorded with the run it starts."""

    async def scenario(h: Harness) -> None:
        await h.start(
            start_signal=None,
            in_flight_run_id="ghost",
            in_flight_operation_count=1,
            reconcile_interval_seconds=10**6,
        )
        await eventually(h.state, lambda s: s["in_flight_started_at"])
        await h.env.sleep(OPERATION_BUDGET + timedelta(minutes=1))
        run_id = (await eventually(h.state, lambda s: s["in_flight_run_id"] not in (None, "ghost")))["in_flight_run_id"]
        [record] = await h.records(1)
        assert record["wake_reasons"] == {"previous_run_finished": 1}
        assert record["run_id"] == run_id
        await h.settle()
        assert len(h.plans.requests) == 1

    _run(scenario, script=lambda _: _planned(COMPACTION, interval=10**6))
