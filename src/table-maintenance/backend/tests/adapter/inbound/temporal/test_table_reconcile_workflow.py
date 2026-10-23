"""Test the TableReconcileWorkflow on a time-skipping Temporal test server."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from temporalio.client import WorkflowExecutionStatus
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from adapter.inbound.temporal.workflows import TableReconcileWorkflow
from adapter.temporal_contracts.table_reconcile_workflow_input import (
    TableReconcileWorkflowInput,
)
from adapter.temporal_contracts.workflow_names import TABLE_RECONCILE_WORKFLOW
from application.domain.model.maintenance.workflow_ids import (
    SIGNAL_MAINTENANCE_FINISHED,
    SIGNAL_PAUSE,
    SIGNAL_RESUME,
    SIGNAL_SETTINGS_CHANGED,
    SIGNAL_STOP,
    SIGNAL_TRIGGER_NOW,
    TASK_QUEUE,
    maintenance_workflow_id,
    table_reconcile_workflow_id,
)
from tests.adapter.inbound.temporal.eventually import eventually
from tests.adapter.inbound.temporal.maintenance_stub_workflow import (
    MaintenanceStubWorkflow,
)
from tests.adapter.inbound.temporal.scripted_plan_activity import ScriptedPlanActivity

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from temporalio.client import Client, WorkflowHandle

UUID = "u1"
WORKFLOW_ID = table_reconcile_workflow_id(UUID)
COMPACTION = "rewrite_data_files"
EXPIRE = "expire_snapshots"
REAL_TIMEOUT_SECONDS = 20


def _planned(*operations: str, interval: int = 3600) -> dict[str, Any]:
    return {
        "status": "planned",
        "reason": None,
        "reconcile_interval_seconds": interval,
        "operations": [
            {"operation": op, "filters": [], "procedure_args": {}} for op in operations
        ],
    }


def _skip(reason: str, interval: int = 3600) -> dict[str, Any]:
    return {
        "status": "skip",
        "reason": reason,
        "reconcile_interval_seconds": interval,
        "operations": [],
    }


@dataclass
class Harness:
    env: WorkflowEnvironment
    client: Client
    plans: ScriptedPlanActivity
    handle: WorkflowHandle | None = None

    async def start(
        self, start_signal: str | None = SIGNAL_RESUME, **fields: Any
    ) -> WorkflowHandle:
        options: dict[str, Any] = {}
        if start_signal is not None:
            options = {"start_signal": start_signal, "start_signal_args": [{}]}
        self.handle = await self.client.start_workflow(
            TABLE_RECONCILE_WORKFLOW,
            TableReconcileWorkflowInput(table_uuid=UUID, **fields),
            id=WORKFLOW_ID,
            task_queue=TASK_QUEUE,
            **options,
        )
        return self.handle

    async def signal(self, name: str, payload: dict | None = None) -> None:
        handle = self.client.get_workflow_handle(WORKFLOW_ID)
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

    async def child(self, run_id: str) -> dict[str, Any]:
        handle = self.client.get_workflow_handle(maintenance_workflow_id(run_id))
        return await handle.query("started_with")

    async def complete_child(self, run_id: str) -> None:
        handle = self.client.get_workflow_handle(maintenance_workflow_id(run_id))
        await handle.signal("complete")

    async def ended(self) -> None:
        handle = self.client.get_workflow_handle(WORKFLOW_ID)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

    async def status(self) -> WorkflowExecutionStatus | None:
        handle = self.client.get_workflow_handle(WORKFLOW_ID)
        return (await handle.describe()).status

    async def settle(self) -> None:
        """Give the worker time to process what was sent before asserting a no-op."""
        await asyncio.sleep(0.5)
        await self.state()


def _run(
    scenario: Callable[[Harness], Awaitable[None]],
    script: Callable[[dict[str, Any]], dict[str, Any]] = lambda _: _planned(),
) -> None:
    async def go() -> None:
        async with await WorkflowEnvironment.start_time_skipping() as env:
            plans = ScriptedPlanActivity(script)
            async with Worker(
                env.client,
                task_queue=TASK_QUEUE,
                workflows=[TableReconcileWorkflow, MaintenanceStubWorkflow],
                activities=[plans.plan_table_maintenance],
            ):
                await scenario(Harness(env, env.client, plans))

    asyncio.run(go())


def test_timer_triggers_plan_every_interval():
    async def scenario(h: Harness) -> None:
        await h.start(start_signal=None)
        await h.env.sleep(timedelta(seconds=3500))
        await h.settle()
        assert h.plans.requests == []
        await h.env.sleep(timedelta(seconds=200))
        first = (await h.plan_count(1))[0]
        assert first["table_uuid"] == UUID
        assert first["manual_operations"] is None
        await h.env.sleep(timedelta(seconds=1500))
        await h.settle()
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

    _run(scenario, script=lambda _: _planned(COMPACTION))


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
        await h.signal(SIGNAL_TRIGGER_NOW, {"operations": [EXPIRE]})
        await h.settle()
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
        await h.plan_count(1)
        await h.settle()
        assert await h.status() == WorkflowExecutionStatus.RUNNING
        await h.signal(SIGNAL_SETTINGS_CHANGED)
        await h.plan_count(2)
        await h.in_flight()

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_planned_empty_starts_no_child():
    async def scenario(h: Harness) -> None:
        await h.start()
        await h.plan_count(1)
        await h.settle()
        assert (await h.state())["in_flight_run_id"] is None

    _run(scenario, script=lambda _: _planned())


def test_in_flight_run_that_never_finishes_is_cleared_after_cap():
    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.env.sleep(timedelta(hours=13))
        await h.settle()
        assert (await h.state())["in_flight_run_id"] is not None
        assert len(h.plans.requests) == 1
        await h.env.sleep(timedelta(hours=1, minutes=1))
        await h.plan_count(2)
        await eventually(h.state, lambda s: s["in_flight_run_id"] not in (None, first))

    _run(scenario, script=lambda _: _planned(COMPACTION, EXPIRE, interval=10**6))
