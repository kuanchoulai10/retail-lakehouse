"""Test the TableReconciliationWorkflow on a time-skipping Temporal test server."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from temporalio.client import WorkflowExecutionStatus
from temporalio.testing import WorkflowEnvironment
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.worker import UnsandboxedWorkflowRunner, Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner

from adapter.hybrid.temporal.inbound.workflows import TableReconciliationWorkflow
from adapter.hybrid.temporal.contracts import (
    TableReconciliationWorkflowInput,
    TABLE_RECONCILIATION_WORKFLOW,
    SIGNAL_MAINTENANCE_FINISHED,
    SIGNAL_PAUSE,
    SIGNAL_RESUME,
    SIGNAL_SETTINGS_CHANGED,
    SIGNAL_STOP,
    SIGNAL_TRIGGER_NOW,
    TASK_QUEUE,
    table_maintenance_workflow_id,
    table_reconciliation_workflow_id,
)
from tests.adapter.hybrid.temporal.inbound.eventually import eventually
from tests.adapter.hybrid.temporal.inbound.table_maintenance_stub_workflow import (
    TableMaintenanceStubWorkflow,
)
from tests.adapter.hybrid.temporal.inbound.scripted_plan_activity import (
    ScriptedPlanActivity,
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


def _planned(*operations: str, interval: int = 3600) -> dict[str, Any]:
    return {
        "status": "planned",
        "reason": None,
        "reconcile_interval_seconds": interval,
        "table_name": TABLE,
        "operations": [
            {"operation": op, "filters": [], "procedure_args": {}} for op in operations
        ],
    }


def _skip(reason: str, interval: int = 3600) -> dict[str, Any]:
    return {
        "status": "skip",
        "reason": reason,
        "reconcile_interval_seconds": interval,
        "table_name": TABLE,
        "operations": [],
    }


def _child_id(run_id: str) -> str:
    return table_maintenance_workflow_id(TABLE, run_id)


def _within_a_second(gap: timedelta, seconds: int) -> bool:
    """Tell whether ``gap`` is ``seconds`` long, allowing for the activity's run time."""
    return timedelta(seconds=seconds) <= gap < timedelta(seconds=seconds + 1)


@dataclass
class Harness:
    env: WorkflowEnvironment
    client: Client
    plans: ScriptedPlanActivity
    handle: WorkflowHandle | None = None
    sent: int = 0

    async def start(
        self, start_signal: str | None = SIGNAL_RESUME, **fields: Any
    ) -> WorkflowHandle:
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
        handle = self.client.get_workflow_handle(WORKFLOW_ID)
        self.sent += 1
        if payload is None:
            await handle.signal(name)
        else:
            await handle.signal(name, payload)

    async def state(self) -> dict[str, Any]:
        return await self.client.get_workflow_handle(WORKFLOW_ID).query("state")

    async def plan_count(self, count: int) -> list[dict[str, Any]]:
        async def probe() -> list[dict[str, Any]]:
            return list(self.plans.requests)

        return await eventually(probe, lambda r: len(r) >= count)

    async def in_flight(self) -> str:
        state = await eventually(self.state, lambda s: s["in_flight_run_id"])
        return state["in_flight_run_id"]

    async def idle_after(self, before: dict[str, Any]) -> dict[str, Any]:
        """Wait until the carried in-flight run of ``before`` is no longer tracked."""
        return await eventually(
            self.state,
            lambda s: (
                s["in_flight_run_id"] != before["in_flight_run_id"]
                and not s["planning"]
            ),
        )

    async def child(self, run_id: str) -> dict[str, Any]:
        handle = self.client.get_workflow_handle(_child_id(run_id))
        return await handle.query("started_with")

    async def child_summary(self, run_id: str) -> str | None:
        handle = self.client.get_workflow_handle(_child_id(run_id))
        return await (await handle.describe()).static_summary()

    async def child_status(self, run_id: str) -> WorkflowExecutionStatus | None:
        handle = self.client.get_workflow_handle(_child_id(run_id))
        return (await handle.describe()).status

    async def complete_child(self, run_id: str) -> None:
        handle = self.client.get_workflow_handle(_child_id(run_id))
        await handle.signal("complete")
        self.sent += 1

    async def ended(self) -> None:
        handle = self.client.get_workflow_handle(WORKFLOW_ID)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

    async def status(self) -> WorkflowExecutionStatus | None:
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
            lambda s: (
                s["signals_handled"] >= self.sent
                and not s["woken"]
                and not s["planning"]
            ),
        )


def _run(
    scenario: Callable[[Harness], Awaitable[None]],
    script: Callable[[dict[str, Any]], dict[str, Any]] = lambda _: _planned(),
    runner: WorkflowRunner | None = None,
) -> None:
    async def go() -> None:
        async with await WorkflowEnvironment.start_time_skipping() as env:
            plans = ScriptedPlanActivity(script)
            async with Worker(
                env.client,
                task_queue=TASK_QUEUE,
                workflows=[TableReconciliationWorkflow, TableMaintenanceStubWorkflow],
                activities=[plans.plan_table_maintenance],
                workflow_runner=runner or SandboxedWorkflowRunner(),
            ):
                await scenario(Harness(env, env.client, plans))

    asyncio.run(go())


def test_timer_triggers_plan_every_interval():
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
        gap = datetime.fromisoformat(second["now"]) - datetime.fromisoformat(
            first["now"]
        )
        assert timedelta(seconds=1800) <= gap < timedelta(seconds=1900)

    _run(scenario, script=lambda _: _planned(interval=1800))


def test_signal_with_start_plans_and_starts_child_with_abandon_semantics():
    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        child = await h.child(run_id)
        assert child["table_uuid"] == UUID
        assert child["parent_workflow_id"] == WORKFLOW_ID
        assert child["trigger"] == "scheduled"
        assert child["plan"] == _planned(COMPACTION)
        assert len(h.plans.requests) == 1
        assert (await h.state())["in_flight_workflow_id"] == (
            f"table-maintenance:table={TABLE}:run={run_id}"
        )

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_child_summary_names_the_table_and_the_planned_operations():
    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        assert await h.child_summary(run_id) == (f"{TABLE} · {COMPACTION}, {EXPIRE}")

    _run(scenario, script=lambda _: _planned(COMPACTION, EXPIRE))


def test_trigger_now_while_in_flight_runs_after_finish():
    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.signal(SIGNAL_TRIGGER_NOW, {"operations": [COMPACTION]})
        await h.signal(SIGNAL_TRIGGER_NOW, {"operations": [EXPIRE]})
        await h.settle()
        assert len(h.plans.requests) == 1
        assert (await h.state())["pending_manual"] == [EXPIRE]
        await h.complete_child(first)
        second_plan = (await h.plan_count(2))[1]
        assert second_plan["manual_operations"] == [EXPIRE]
        second = await eventually(
            h.state, lambda s: s["in_flight_run_id"] not in (None, first)
        )
        assert second["pending_manual"] is None
        child = await h.child(second["in_flight_run_id"])
        assert child["trigger"] == "manual"

    _run(scenario, script=lambda r: _planned(*(r["manual_operations"] or [COMPACTION])))


def test_trigger_now_without_operations_plans_all_due_as_manual():
    async def scenario(h: Harness) -> None:
        await h.start(start_signal=SIGNAL_TRIGGER_NOW)
        run_id = await h.in_flight()
        assert h.plans.requests[0]["manual_operations"] is None
        assert (await h.child(run_id))["trigger"] == "manual"

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_child_result_received_after_continue_as_new():
    async def scenario(h: Harness) -> None:
        handle = await h.start(continue_as_new_after=2)
        first_run = handle.result_run_id
        run_id = await h.in_flight()
        await h.signal(SIGNAL_TRIGGER_NOW, {"operations": [EXPIRE]})
        for _ in range(3):
            await h.signal(SIGNAL_SETTINGS_CHANGED)

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
    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        await h.signal(
            SIGNAL_MAINTENANCE_FINISHED, {"run_id": "other", "record_failures": 0}
        )
        await h.settle()
        assert (await h.state())["in_flight_run_id"] == run_id
        assert len(h.plans.requests) == 1

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_dropped_signal_ends_workflow_after_in_flight_run():
    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        await h.signal(SIGNAL_STOP)
        state = await h.settle()
        assert state["stopping"] is True
        assert state["in_flight_run_id"] == run_id
        assert await h.status() == WorkflowExecutionStatus.RUNNING
        await h.complete_child(run_id)
        await h.ended()
        assert len(h.plans.requests) == 1

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_stop_with_nothing_in_flight_ends_immediately():
    async def scenario(h: Harness) -> None:
        await h.start(start_signal=None)
        await h.signal(SIGNAL_STOP)
        await h.ended()
        assert h.plans.requests == []

    _run(scenario)


def test_skip_excluded_ends_workflow():
    async def scenario(h: Harness) -> None:
        await h.start()
        await h.ended()
        assert len(h.plans.requests) == 1

    _run(scenario, script=lambda _: _skip("excluded"))


def test_skip_dropped_ends_workflow():
    async def scenario(h: Harness) -> None:
        await h.start()
        await h.ended()

    _run(scenario, script=lambda _: _skip("dropped"))


def test_pause_skips_plans_resume_restores():
    paused = {"value": True}

    def script(_: dict[str, Any]) -> dict[str, Any]:
        return _skip("paused") if paused["value"] else _planned(COMPACTION)

    async def scenario(h: Harness) -> None:
        await h.start()
        await h.plan_count(1)
        await h.signal(SIGNAL_PAUSE)
        await h.plan_count(2)
        await h.settle()
        assert (await h.state())["in_flight_run_id"] is None
        assert await h.status() == WorkflowExecutionStatus.RUNNING
        paused["value"] = False
        await h.signal(SIGNAL_RESUME)
        run_id = await h.in_flight()
        assert (await h.child(run_id))["trigger"] == "scheduled"
        assert len(h.plans.requests) == 3

    _run(scenario, script=script)


def test_manual_trigger_on_paused_table_is_dropped():
    paused = {"value": True}

    def script(_: dict[str, Any]) -> dict[str, Any]:
        return _skip("paused") if paused["value"] else _planned(COMPACTION)

    async def scenario(h: Harness) -> None:
        await h.start(start_signal=None)
        await h.signal(SIGNAL_TRIGGER_NOW, {"operations": [EXPIRE]})
        assert (await h.plan_count(1))[0]["manual_operations"] == [EXPIRE]
        await h.settle()
        assert (await h.state())["pending_manual"] is None
        paused["value"] = False
        await h.signal(SIGNAL_RESUME)
        assert (await h.plan_count(2))[1]["manual_operations"] is None
        run_id = await h.in_flight()
        assert (await h.child(run_id))["trigger"] == "scheduled"

    _run(scenario, script=script)


def test_plan_failure_does_not_fail_workflow():
    async def scenario(h: Harness) -> None:
        h.plans.failures = 1
        await h.start()
        failed = (await h.plan_count(1))[0]
        state = await h.settle()
        assert state["in_flight_run_id"] is None
        due = datetime.fromisoformat(state["next_plan_at"])
        assert _within_a_second(due - datetime.fromisoformat(failed["now"]), 3600)
        assert await h.status() == WorkflowExecutionStatus.RUNNING
        await h.signal(SIGNAL_SETTINGS_CHANGED)
        await h.plan_count(2)
        await h.in_flight()

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_planned_empty_starts_no_child():
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
        await eventually(h.state, lambda s: s["in_flight_run_id"] not in (None, first))

    _run(scenario, script=lambda _: _planned(COMPACTION, EXPIRE, interval=10**6))


def test_give_up_cancels_the_stale_child_before_starting_a_new_run():
    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.env.sleep(OPERATION_BUDGET + timedelta(minutes=1))
        await h.plan_count(2)
        second = (
            await eventually(
                h.state, lambda s: s["in_flight_run_id"] not in (None, first)
            )
        )["in_flight_run_id"]
        assert await h.child_status(first) == WorkflowExecutionStatus.CANCELED
        assert await h.child_status(second) == WorkflowExecutionStatus.RUNNING

    _run(scenario, script=lambda _: _planned(COMPACTION, interval=10**6))


def test_give_up_waits_a_grace_for_a_child_that_ignores_its_cancel():
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
        await eventually(h.state, lambda s: s["in_flight_run_id"] not in (None, first))

    _run(scenario, script=lambda _: plan)


def test_include_after_exclude_while_in_flight_keeps_workflow():
    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.signal(SIGNAL_STOP)
        await h.signal(SIGNAL_RESUME)
        assert (await h.settle())["stopping"] is False
        await h.complete_child(first)
        await h.plan_count(2)
        await eventually(h.state, lambda s: s["in_flight_run_id"] not in (None, first))
        assert await h.status() == WorkflowExecutionStatus.RUNNING

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_excluded_plan_with_wake_during_activity_replans():
    answers = [_skip("excluded"), _planned(COMPACTION)]

    async def scenario(h: Harness) -> None:
        h.plans.gate = asyncio.Event()
        await h.start()
        await h.plan_count(1)
        await h.signal(SIGNAL_RESUME)
        await eventually(h.state, lambda s: s["signals_handled"] >= h.sent)
        h.plans.gate.set()
        await h.plan_count(2)
        await h.in_flight()
        assert await h.status() == WorkflowExecutionStatus.RUNNING

    _run(scenario, script=lambda _: answers.pop(0))


def test_stop_during_plan_starts_no_child():
    async def scenario(h: Harness) -> None:
        h.plans.gate = asyncio.Event()
        await h.start()
        await h.plan_count(1)
        await h.signal(SIGNAL_STOP)
        await eventually(h.state, lambda s: s["stopping"])
        h.plans.gate.set()
        await h.ended()
        assert len(h.plans.requests) == 1

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_continue_as_new_carries_interval_used_after_plan_failure():
    async def scenario(h: Harness) -> None:
        await h.start(continue_as_new_after=1)
        await h.plan_count(1)
        h.plans.failures = 1
        await h.env.sleep(timedelta(seconds=610))
        failed = (await h.plan_count(2))[1]
        await h.env.sleep(timedelta(seconds=610))
        third = (await h.plan_count(3))[2]
        gap = datetime.fromisoformat(third["now"]) - datetime.fromisoformat(
            failed["now"]
        )
        assert timedelta(seconds=600) <= gap < timedelta(seconds=700)

    _run(scenario, script=lambda _: _planned(interval=600))


def test_carried_in_flight_run_without_start_time_gets_a_fixed_deadline():
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
    async def scenario(h: Harness) -> None:
        await h.start(
            start_signal=None, in_flight_run_id="ghost", in_flight_operation_count=1
        )
        state = await eventually(h.state, lambda s: s["in_flight_started_at"])
        assert state["in_flight_workflow_id"] is None
        await h.env.sleep(OPERATION_BUDGET + timedelta(minutes=1))
        await h.plan_count(1)
        await h.idle_after(state)

    _run(scenario, script=lambda _: _planned())


def test_child_start_failure_keeps_workflow_alive(monkeypatch: pytest.MonkeyPatch):
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
        await h.signal(SIGNAL_SETTINGS_CHANGED)
        await h.plan_count(2)
        run_id = await h.in_flight()
        assert (await h.child(run_id))["plan"] == _planned(EXPIRE)

    _run(
        scenario,
        script=lambda _: answers.pop(0),
        runner=UnsandboxedWorkflowRunner(),
    )
