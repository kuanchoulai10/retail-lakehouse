"""Test the TableReconciliationWorkflow on a time-skipping Temporal test server."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from temporalio.client import WorkflowExecutionStatus, WorkflowHistory
from temporalio.common import SearchAttributeKey
from temporalio.converter import DataConverter
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer, UnsandboxedWorkflowRunner, Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    TABLE_MAINTENANCE_WORKFLOW,
    TableMaintenanceSignal,
    TableMaintenanceWorkflowInput,
    table_maintenance_workflow_id,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TABLE_RECONCILIATION_WORKFLOW,
    TableReconciliationSignal,
    TableReconciliationWorkflowInput,
    table_reconciliation_workflow_id,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import (
    TableMaintenanceActivityPolicy,
    TableMaintenanceAttemptPolicy,
    TableReconciliationWorkflow,
)
from shared_kernel import prefixed_id_pattern
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.eventually import (
    eventually,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.register_table_search_attributes import (
    register_table_search_attributes,
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
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.table_reconciliation_activities_with_fakes import (  # noqa: E501
    table_reconciliation_activities_with_fakes,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from temporalio.client import Client, WorkflowHandle
    from temporalio.common import TypedSearchAttributes
    from temporalio.worker import WorkflowRunner

GHOST_RUN_ID = "mr-00000000000000000000000009"
OTHER_RUN_ID = "mr-00000000000000000000000008"
GONE_CHILD_ID = "table-maintenance:table-uuid=gone"

UUID = "u1"
TABLE = "iceberg.e2e.t"
WORKFLOW_ID = table_reconciliation_workflow_id(UUID)
CHILD_ID = table_maintenance_workflow_id(UUID)
COMPACTION = "rewrite_data_files"
EXPIRE = "expire_snapshots"
REAL_TIMEOUT_SECONDS = 20
TABLE_UUID_KEY = SearchAttributeKey.for_keyword("TableUuid")
TABLE_NAME_KEY = SearchAttributeKey.for_keyword("TableName")
OPERATIONS_KEY = SearchAttributeKey.for_keyword_list("MaintenanceOperations")
TRIGGER_KEY = SearchAttributeKey.for_keyword("MaintenanceTrigger")
RUN_ID_SHAPE = prefixed_id_pattern("mr")
RECONCILIATION_ID_SHAPE = prefixed_id_pattern("rc")
CLOSING_BOUND = TableMaintenanceActivityPolicy().worst_case()


def _check(operation: str, verdict: str = "due") -> dict[str, Any]:
    return {
        "operation": operation,
        "verdict": verdict,
        "measurements": [],
        "next_eligible_at": None,
    }


NIGHTLY_POLICY_ID = "mp-00000000000000000000000004"
POLICY = {
    "policy_id": NIGHTLY_POLICY_ID,
    "policy_name": "nightly",
    "policy_version": 4,
    "policy_target": {"type": "catalog", "path": ["prod"]},
}
NO_POLICY = {"policy_id": None, "policy_name": None, "policy_version": None, "policy_target": None}


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
        **POLICY,
    }


def _with_candidates(plan: dict[str, Any]) -> dict[str, Any]:
    """Return ``plan`` with its compaction naming a candidate partition, as plans did before whole-table compaction."""
    operations = [
        {**op, "candidate_partitions": [{"spec_id": 0, "values": ["eu"]}]} if op["operation"] == COMPACTION else op
        for op in plan["operations"]
    ]
    return {**plan, "operations": operations}


def _with_next_check(next_check_in: int) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Return a plan carrying a ``next_check_at`` ``next_check_in`` seconds on, as plans did for held candidates."""

    def answer(request: dict[str, Any]) -> dict[str, Any]:
        at = datetime.fromisoformat(request["now"]) + timedelta(seconds=next_check_in)
        return {**_planned(), "next_check_at": at.isoformat()}

    return answer


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
        **(POLICY if table_found else NO_POLICY),
    }


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

    async def start(
        self, start_signal: str | None = TableReconciliationSignal.TABLE_SEEN, **fields: Any
    ) -> WorkflowHandle:
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

    async def start_with_a_gone_child(self, **fields: Any) -> WorkflowHandle:
        """Start the workflow carrying a run in flight whose child workflow does not exist, so no signal reaches it."""
        return await self.start(
            start_signal=None,
            in_flight_run_id=GHOST_RUN_ID,
            in_flight_workflow_id=GONE_CHILD_ID,
            in_flight_operation_count=1,
            **fields,
        )

    async def report_gone_child(self, *, unapplied_raise: bool = False) -> None:
        """Report the carried run in flight finished, as its child would have."""
        await self.signal(
            TableReconciliationSignal.MAINTENANCE_FINISHED,
            {"run_id": GHOST_RUN_ID, "record_failures": 0, "unapplied_raise": unapplied_raise},
        )

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

    async def child_handle(self, run_id: str) -> WorkflowHandle:
        """Return the handle of the child execution of a run.

        Every run of the table runs under the table's one workflow id, so the
        execution of a run is found in the reconciliation's history (all its
        runs, across continue-as-new) and the handle pins its Temporal run id.
        """

        async def started() -> dict[str, str]:
            return await self._started_children()

        children = await eventually(started, lambda found: run_id in found)
        return self.client.get_workflow_handle(CHILD_ID, run_id=children[run_id])

    async def _started_children(self) -> dict[str, str]:
        """Map each maintenance run id the reconciliation started to its child's Temporal run id."""
        converter = DataConverter.default.payload_converter
        found: dict[str, str] = {}
        temporal_run: str | None = (await self.client.get_workflow_handle(WORKFLOW_ID).describe()).run_id
        while temporal_run:
            history = await self.client.get_workflow_handle(WORKFLOW_ID, run_id=temporal_run).fetch_history()
            temporal_run = None
            initiated: dict[int, str] = {}
            for event in history.events:
                if event.HasField("workflow_execution_started_event_attributes"):
                    temporal_run = event.workflow_execution_started_event_attributes.continued_execution_run_id
                elif event.HasField("start_child_workflow_execution_initiated_event_attributes"):
                    payloads = event.start_child_workflow_execution_initiated_event_attributes.input.payloads
                    initiated[event.event_id] = converter.from_payloads(payloads)[0]["run_id"]
                elif event.HasField("child_workflow_execution_started_event_attributes"):
                    child = event.child_workflow_execution_started_event_attributes
                    found[initiated[child.initiated_event_id]] = child.workflow_execution.run_id
        return found

    async def scheduled_activities(self) -> list[str]:
        """Return the names of the activities the reconciliation's current execution scheduled, in order."""
        history = await self.client.get_workflow_handle(WORKFLOW_ID).fetch_history()
        return [
            e.activity_task_scheduled_event_attributes.activity_type.name
            for e in history.events
            if e.HasField("activity_task_scheduled_event_attributes")
        ]

    async def child(self, run_id: str) -> dict[str, Any]:
        """Query the stub child of a run for the input it started with."""
        return await (await self.child_handle(run_id)).query("started_with")

    async def child_summary(self, run_id: str) -> str | None:
        """Return the static summary of the child workflow of a run."""
        return await (await (await self.child_handle(run_id)).describe()).static_summary()

    async def child_search_attributes(self, run_id: str) -> TypedSearchAttributes:
        """Return the search attributes the child workflow of a run started with."""
        return (await (await self.child_handle(run_id)).describe()).typed_search_attributes

    async def search_attributes(self) -> TypedSearchAttributes:
        """Return the search attributes of the reconciliation workflow."""
        return (await self.client.get_workflow_handle(WORKFLOW_ID).describe()).typed_search_attributes

    async def child_status(self, run_id: str) -> WorkflowExecutionStatus | None:
        """Return the execution status of the child workflow of a run."""
        return (await (await self.child_handle(run_id)).describe()).status

    async def complete_child(self, run_id: str) -> None:
        """Signal the stub child of a run to finish."""
        await (await self.child_handle(run_id)).signal("complete")
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
    *,
    max_cached_workflows: int = 1000,
) -> None:
    async def go() -> None:
        async with await WorkflowEnvironment.start_time_skipping() as env:
            await register_table_search_attributes(env.client)
            plans = ScriptedPlanActivity(script)
            recorder = ScriptedRecordActivity()
            lookups = table_reconciliation_activities_with_fakes(client=env.client)
            async with Worker(
                env.client,
                task_queue=TASK_QUEUE,
                workflows=[TableReconciliationWorkflow, TableMaintenanceStubWorkflow],
                activities=[
                    plans.plan_table_maintenance,
                    recorder.record_table_reconciliation,
                    lookups.get_workflow_running,
                ],
                workflow_runner=runner or SandboxedWorkflowRunner(),
                max_cached_workflows=max_cached_workflows,
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
        assert (await h.state())["in_flight_workflow_id"] == CHILD_ID

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_child_runs_under_the_table_workflow_id():
    """The child runs under the table's maintenance workflow id, named by the table uuid."""

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        assert (await h.state())["in_flight_workflow_id"] == f"table-maintenance:table-uuid={UUID}"
        assert (await (await h.child_handle(run_id)).describe()).id == f"table-maintenance:table-uuid={UUID}"

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_second_run_for_the_table_is_refused_while_one_runs():
    """A run already running under the table's workflow id refuses the next start, recorded as a failed start."""

    async def scenario(h: Harness) -> None:
        await h.client.start_workflow(
            TABLE_MAINTENANCE_WORKFLOW,
            TableMaintenanceWorkflowInput(
                run_id=OTHER_RUN_ID,
                table_uuid=UUID,
                parent_workflow_id="elsewhere",
                trigger="manual",
                plan=_planned(COMPACTION),
            ),
            id=CHILD_ID,
            task_queue=TASK_QUEUE,
        )
        await h.start()
        record = (await h.records(1))[0]
        assert (await h.settle())["in_flight_run_id"] is None
        assert record["run_id"] is None
        assert record["run_start_failed"] is True
        started_with = await h.client.get_workflow_handle(CHILD_ID).query("started_with")
        assert started_with["run_id"] == OTHER_RUN_ID

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_next_run_reuses_the_id_after_the_first_closed():
    """Once a table's run has closed, the next run starts under the same workflow id."""

    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.complete_child(first)
        second = (await eventually(h.state, lambda s: s["in_flight_run_id"] not in (None, first)))["in_flight_run_id"]
        assert (await h.state())["in_flight_workflow_id"] == CHILD_ID
        assert await h.child_status(first) == WorkflowExecutionStatus.COMPLETED
        assert await h.child_status(second) == WorkflowExecutionStatus.RUNNING
        assert (await h.child(second))["run_id"] == second
        records = await h.records(2)
        assert [r["run_start_failed"] for r in records[:2]] == [False, False]

    _run(scenario, script=lambda _: {**_planned(COMPACTION), "stub_lingers_seconds": 1})


def test_child_summary_names_the_table_and_the_planned_operations():
    """The child workflow summary names the table and the planned operations."""

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        assert await h.child_summary(run_id) == (f"{TABLE} · {COMPACTION}, {EXPIRE}")

    _run(scenario, script=lambda _: _planned(COMPACTION, EXPIRE))


@pytest.mark.parametrize(
    ("start_signal", "trigger"),
    [
        (TableReconciliationSignal.TABLE_SEEN, "scheduled"),
        (TableReconciliationSignal.TRIGGER_NOW, "manual"),
    ],
)
def test_maintenance_run_carries_table_search_attributes(start_signal: str, trigger: str):
    """The run is tagged with its table, its planned operations and what triggered it."""

    async def scenario(h: Harness) -> None:
        await h.start(start_signal=start_signal)
        run_id = await h.in_flight()
        attributes = await h.child_search_attributes(run_id)
        assert attributes.get(TABLE_UUID_KEY) == UUID
        assert attributes.get(TABLE_NAME_KEY) == TABLE
        assert list(attributes.get(OPERATIONS_KEY) or []) == [COMPACTION, EXPIRE]
        assert attributes.get(TRIGGER_KEY) == trigger

    _run(scenario, script=lambda _: _planned(COMPACTION, EXPIRE))


def test_reconciliation_upserts_its_table_uuid():
    """A reconciliation started without search attributes tags itself with its table and its name."""

    async def scenario(h: Harness) -> None:
        await h.start()
        await h.in_flight()
        attributes = await eventually(h.search_attributes, lambda a: a.get(TABLE_NAME_KEY) is not None)
        assert attributes.get(TABLE_UUID_KEY) == UUID
        assert attributes.get(TABLE_NAME_KEY) == TABLE

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_reconciliation_follows_a_renamed_table():
    """When a later plan names the table differently, the reconciliation's table name follows it."""
    renamed = "iceberg.e2e.renamed"

    async def scenario(h: Harness) -> None:
        await h.start()
        await h.plan_count(1)
        await eventually(h.search_attributes, lambda a: a.get(TABLE_NAME_KEY) == TABLE)
        await h.signal(TableReconciliationSignal.RECONCILE_NOW)
        await h.plan_count(2)
        attributes = await eventually(h.search_attributes, lambda a: a.get(TABLE_NAME_KEY) == renamed)
        assert attributes.get(TABLE_UUID_KEY) == UUID

    names = iter([TABLE, renamed])
    _run(scenario, script=lambda _: {**_planned(), "table_name": next(names, renamed)})


def test_trigger_now_while_in_flight_runs_after_finish():
    """A manual trigger during a run whose child cannot be signalled is kept and planned after the run finishes."""

    async def scenario(h: Harness) -> None:
        await h.start_with_a_gone_child()
        await h.signal(TableReconciliationSignal.TRIGGER_NOW, {"operations": [COMPACTION]})
        await h.signal(TableReconciliationSignal.TRIGGER_NOW, {"operations": [EXPIRE]})
        await h.settle()
        assert h.plans.requests == []
        assert (await h.state())["pending_manual"] == [EXPIRE]
        await h.report_gone_child()
        plan = (await h.plan_count(1))[0]
        assert plan["manual_operations"] == [EXPIRE]
        run = await eventually(h.state, lambda s: s["in_flight_run_id"] not in (None, GHOST_RUN_ID))
        assert run["pending_manual"] is None
        child = await h.child(run["in_flight_run_id"])
        assert child["trigger"] == "manual"

    _run(scenario, script=lambda r: _planned(*(r["manual_operations"] or [COMPACTION])))


def test_trigger_now_priority_reaches_the_manual_plan_only():
    """A kept manual trigger's priority goes to its plan; the plan after its run carries none."""

    async def scenario(h: Harness) -> None:
        await h.start_with_a_gone_child()
        await h.signal(TableReconciliationSignal.TRIGGER_NOW, {"operations": [EXPIRE], "priority": "P0"})
        await h.settle()
        assert (await h.state())["pending_manual_priority"] == "P0"
        await h.report_gone_child()
        assert (await h.plan_count(1))[0]["manual_priority"] == "P0"
        run = await eventually(h.state, lambda s: s["in_flight_run_id"] not in (None, GHOST_RUN_ID))
        assert run["pending_manual_priority"] is None
        await h.complete_child(run["in_flight_run_id"])
        assert (await h.plan_count(2))[1]["manual_priority"] is None

    _run(scenario, script=lambda r: _planned(*(r["manual_operations"] or [COMPACTION])))


def test_a_later_trigger_without_priority_clears_the_pending_priority():
    """A second manual trigger replaces the first, so one that names no priority clears it."""

    async def scenario(h: Harness) -> None:
        await h.start_with_a_gone_child()
        await h.signal(TableReconciliationSignal.TRIGGER_NOW, {"operations": [EXPIRE], "priority": "P0"})
        await h.signal(TableReconciliationSignal.TRIGGER_NOW, {"operations": [EXPIRE]})
        await h.settle()
        assert (await h.state())["pending_manual_priority"] is None
        await h.report_gone_child()
        assert (await h.plan_count(1))[0]["manual_priority"] is None

    _run(scenario, script=lambda r: _planned(*(r["manual_operations"] or [COMPACTION])))


def test_trigger_now_priority_survives_continue_as_new():
    """A pending manual priority is carried through continue as new."""

    async def scenario(h: Harness) -> None:
        handle = await h.start_with_a_gone_child(continue_as_new_after=2)
        first_run = handle.result_run_id
        await h.signal(TableReconciliationSignal.TRIGGER_NOW, {"operations": [EXPIRE], "priority": "P1"})
        await h.settle()
        for _ in range(3):
            await h.signal(TableReconciliationSignal.POLICY_CHANGED)

        async def run_id_now() -> str | None:
            return (await h.client.get_workflow_handle(WORKFLOW_ID).describe()).run_id

        await eventually(run_id_now, lambda r: r != first_run)
        assert (await h.state())["pending_manual_priority"] == "P1"
        await h.report_gone_child()
        plan = (await h.plan_count(1))[0]
        assert (plan["manual_operations"], plan["manual_priority"]) == ([EXPIRE], "P1")

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_manual_trigger_in_flight_signals_the_child():
    """A manual trigger while a run is in flight raises that run's priority instead of planning another."""

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        await h.signal(TableReconciliationSignal.TRIGGER_NOW, {"operations": [EXPIRE], "priority": "P0"})
        child = await h.child_handle(run_id)

        async def raises() -> list[str | None]:
            return await child.query("raises")

        await eventually(raises, lambda r: r == ["P0"])
        state = await eventually(h.state, lambda s: s["pending_manual"] is None)
        assert state["pending_manual_priority"] is None
        assert "manual_run" not in state["wake_reasons"]
        await h.complete_child(run_id)
        plan = (await h.plan_count(2))[1]
        assert (plan["manual_operations"], plan["manual_priority"]) == (None, None)
        assert (await h.records(2))[1]["wake_reasons"] == {"previous_run_finished": 1}

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_manual_trigger_without_priority_raises_to_the_table_priority():
    """A manual trigger that names no priority asks the run in flight for the table's priority."""

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        await h.signal(TableReconciliationSignal.TRIGGER_NOW, {"operations": [EXPIRE]})
        child = await h.child_handle(run_id)

        async def raises() -> list[str | None]:
            return await child.query("raises")

        await eventually(raises, lambda r: r == [None])

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_manual_trigger_to_a_gone_child_is_planned_after_the_report():
    """A manual trigger whose raise cannot reach the run in flight stays pending and is planned once it reports."""

    async def scenario(h: Harness) -> None:
        await h.start_with_a_gone_child()
        await h.signal(TableReconciliationSignal.TRIGGER_NOW, {"operations": [EXPIRE], "priority": "P1"})
        await h.settle()
        state = await h.state()
        assert (state["pending_manual"], state["pending_manual_priority"]) == ([EXPIRE], "P1")
        assert state["wake_reasons"] == {"manual_run": 1}
        await h.report_gone_child()
        plan = (await h.plan_count(1))[0]
        assert (plan["manual_operations"], plan["manual_priority"]) == ([EXPIRE], "P1")
        assert (await h.records(1))[0]["wake_reasons"] == {"manual_run": 1, "previous_run_finished": 1}

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
        for _ in range(4):
            await h.signal(TableReconciliationSignal.POLICY_CHANGED)

        async def run_id_now() -> str | None:
            return (await h.client.get_workflow_handle(WORKFLOW_ID).describe()).run_id

        await eventually(run_id_now, lambda r: r != first_run)
        state = await h.state()
        assert state["in_flight_run_id"] == run_id
        assert state["in_flight_workflow_id"] == CHILD_ID
        assert len(h.plans.requests) == 1
        await h.complete_child(run_id)
        await h.plan_count(2)

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_stale_maintenance_finished_is_ignored():
    """A finished signal for a run that is not in flight is ignored."""

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        await h.signal(
            TableReconciliationSignal.MAINTENANCE_FINISHED,
            {"run_id": OTHER_RUN_ID, "record_failures": 0},
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


def test_skip_unmanaged_ends_workflow():
    """A plan that skips an unmanaged table ends the workflow."""

    async def scenario(h: Harness) -> None:
        await h.start()
        await h.ended()
        assert len(h.plans.requests) == 1
        [record] = h.recorder.records
        assert record["status"] == "skip"
        assert record["skip_reason"] == "unmanaged"
        assert record["wake_reasons"] == {"discovery_scan": 1}

    _run(scenario, script=lambda _: _skip("unmanaged"))


def test_skip_dropped_ends_workflow():
    """A plan that skips a dropped table ends the workflow."""

    async def scenario(h: Harness) -> None:
        await h.start()
        await h.ended()

    _run(scenario, script=lambda _: _skip("dropped"))


def test_unmanaged_reason_ends_workflow_after_in_flight_run():
    """A table unmanaged while a run is in flight ends the workflow only after the run reports back."""
    unmanaged = {"value": False}

    def script(_: dict[str, Any]) -> dict[str, Any]:
        return _skip("unmanaged") if unmanaged["value"] else _planned(COMPACTION)

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        unmanaged["value"] = True
        await h.signal(TableReconciliationSignal.TABLE_UPDATED)
        state = await h.settle()
        assert state["in_flight_run_id"] == run_id
        assert len(h.plans.requests) == 1
        assert await h.status() == WorkflowExecutionStatus.RUNNING
        await h.complete_child(run_id)
        await h.ended()
        assert len(h.plans.requests) == 2
        assert h.recorder.records[-1]["skip_reason"] == "unmanaged"

    _run(scenario, script=script)


def test_manual_trigger_on_a_table_missing_from_the_catalog_is_dropped():
    """A manual trigger on a table the catalog does not have is planned once and then dropped."""
    missing = {"value": True}

    def script(_: dict[str, Any]) -> dict[str, Any]:
        return _skip("not_found") if missing["value"] else _planned(COMPACTION)

    async def scenario(h: Harness) -> None:
        await h.start(start_signal=None)
        await h.signal(TableReconciliationSignal.TRIGGER_NOW, {"operations": [EXPIRE]})
        assert (await h.plan_count(1))[0]["manual_operations"] == [EXPIRE]
        await h.settle()
        assert (await h.state())["pending_manual"] is None
        missing["value"] = False
        await h.signal(TableReconciliationSignal.TABLE_UPDATED)
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
        await h.signal(TableReconciliationSignal.POLICY_CHANGED)
        await h.plan_count(2)
        await h.in_flight()
        assert (await h.records(1))[0]["wake_reasons"] == {"policy_changed": 1}

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


# Per planned operation: 3 attempts of a 24 h queue wait, a 6 h deadline and a 15 min fence,
# backoffs of 60 s + 120 s, 1 h margin.
OPERATION_BUDGET = timedelta(hours=91, minutes=48)


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
        assert [r["wake_reasons"] for r in h.recorder.records] == [{"discovery_scan": 1}, {"previous_run_finished": 1}]

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


def test_give_up_waits_for_a_cancelled_child_that_is_still_running():
    """A given-up run whose child keeps running after its cancel blocks every new run until the child is done."""
    plan = {**_planned(COMPACTION, interval=10**6), "stub_ignores_cancel": True}

    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.env.sleep(OPERATION_BUDGET + timedelta(hours=3))
        state = await h.settle()
        assert state["in_flight_run_id"] == first
        assert len(h.plans.requests) == 1
        assert await h.child_status(first) == WorkflowExecutionStatus.RUNNING
        await h.complete_child(first)
        await h.plan_count(2)
        await eventually(h.state, lambda s: s["in_flight_run_id"] not in (None, first) and not s["planning"])
        assert [r["wake_reasons"] for r in h.recorder.records] == [{"discovery_scan": 1}, {"previous_run_finished": 1}]

    _run(scenario, script=lambda _: plan)


def test_give_up_forgets_a_cancelled_child_that_closed_without_reporting():
    """A cancelled child that closed without reporting is noticed within the grace, and the next run starts."""
    plan = {**_planned(COMPACTION, interval=10**6), "stub_ignores_cancel": True}

    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.env.sleep(OPERATION_BUDGET + timedelta(minutes=5))
        assert (await h.settle())["in_flight_run_id"] == first
        await (await h.child_handle(first)).terminate()
        await h.env.sleep(timedelta(minutes=12))
        await h.plan_count(2)
        await eventually(h.state, lambda s: s["in_flight_run_id"] not in (None, first) and not s["planning"])

    _run(scenario, script=lambda _: plan)


def test_history_that_gave_a_run_up_before_this_milestone_replays():
    """A reconciliation that gave a run up under the bound and grace from before fencing replays on the new code."""

    async def go() -> None:
        fixture = Path(__file__).parent / "fixtures" / "reconciliation_give_up_before_fencing.json"
        history = WorkflowHistory.from_json(WORKFLOW_ID, fixture.read_text())
        await Replayer(workflows=[TableReconciliationWorkflow]).replay_workflow(history)

    asyncio.run(go())


def test_managed_again_while_in_flight_keeps_workflow():
    """A table managed again while a run is in flight keeps the workflow from stopping."""

    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.signal(TableReconciliationSignal.STOP)
        await h.signal(TableReconciliationSignal.TABLE_SEEN)
        assert (await h.settle())["stopping"] is False
        await h.complete_child(first)
        await h.plan_count(2)
        await eventually(h.state, lambda s: s["in_flight_run_id"] not in (None, first))
        assert await h.status() == WorkflowExecutionStatus.RUNNING

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_unmanaged_plan_with_wake_during_activity_replans():
    """An unmanaged plan followed by a wake signal during the activity plans again."""
    answers = [_skip("unmanaged"), _planned(COMPACTION)]

    async def scenario(h: Harness) -> None:
        h.plans.gate = asyncio.Event()
        await h.start()
        await h.plan_count(1)
        await h.signal(TableReconciliationSignal.TABLE_SEEN)
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
            in_flight_run_id=GHOST_RUN_ID,
            in_flight_workflow_id=CHILD_ID,
            in_flight_operation_count=1,
        )
        state = await eventually(h.state, lambda s: s["in_flight_started_at"])
        await h.env.sleep(OPERATION_BUDGET - timedelta(minutes=1))
        assert (await h.settle())["in_flight_run_id"] == GHOST_RUN_ID
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
        await h.start(start_signal=None, in_flight_run_id=GHOST_RUN_ID, in_flight_operation_count=1)
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
        await h.signal(TableReconciliationSignal.POLICY_CHANGED)
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
        assert record["policy_id"] == NIGHTLY_POLICY_ID
        assert record["policy_name"] == "nightly"
        assert record["policy_version"] == 4
        assert record["policy_target"] == {"type": "catalog", "path": ["prod"]}

    _run(scenario, script=lambda _: {**_planned(), "checks": [_check(COMPACTION, "not_needed")]})


def test_a_plan_from_before_policy_ids_is_recorded_without_a_policy_id():
    """A plan an older worker returned names its policy instead of its id; the loop still records it, with no id."""

    async def scenario(h: Harness) -> None:
        await h.start(start_signal=None)
        await h.env.sleep(timedelta(seconds=3700))
        record = (await h.records(1))[0]
        assert record["policy_id"] is None
        assert record["policy_version"] == 4

    older = {key: value for key, value in _planned().items() if key != "policy_id"} | {"policy_name": "nightly"}
    _run(scenario, script=lambda _: older)


def test_three_catalog_commits_during_a_run_are_recorded_after_it_finishes():
    """Wakes that arrive while a run is in flight are kept and recorded by the plan after it finishes."""
    answers = [_planned(COMPACTION), _planned()]

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        first = (await h.records(1))[0]
        assert first["wake_reasons"] == {"discovery_scan": 1}
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
            await h.signal(TableReconciliationSignal.POLICY_CHANGED)

        async def run_id_now() -> str | None:
            return (await h.client.get_workflow_handle(WORKFLOW_ID).describe()).run_id

        await eventually(run_id_now, lambda r: r != first_run)
        assert (await h.state())["wake_reasons"] == {"policy_changed": 3}
        await h.complete_child(run_id)
        second = (await h.records(2))[1]
        assert second["wake_reasons"] == {"policy_changed": 3, "previous_run_finished": 1}

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
        assert first["wake_reasons"] == {"discovery_scan": 1}
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
            {"discovery_scan": 1},
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
            in_flight_run_id=GHOST_RUN_ID,
            in_flight_operation_count=1,
            reconcile_interval_seconds=10**6,
        )
        await eventually(h.state, lambda s: s["in_flight_started_at"])
        await h.env.sleep(OPERATION_BUDGET + timedelta(minutes=1))
        run_id = (await eventually(h.state, lambda s: s["in_flight_run_id"] not in (None, GHOST_RUN_ID)))[
            "in_flight_run_id"
        ]
        [record] = await h.records(1)
        assert record["wake_reasons"] == {"previous_run_finished": 1}
        assert record["run_id"] == run_id
        await h.settle()
        assert len(h.plans.requests) == 1

    _run(scenario, script=lambda _: _planned(COMPACTION, interval=10**6))


def test_discovery_scan_is_recorded_as_its_own_wake_reason():
    """A discovery scan that sees the table wakes the loop and is recorded as a discovery scan."""

    async def scenario(h: Harness) -> None:
        await h.start()
        await h.records(1)
        await h.signal(TableReconciliationSignal.TABLE_SEEN)
        second = (await h.records(2))[1]
        assert second["wake_reasons"] == {"discovery_scan": 1}

    _run(scenario, script=lambda _: _planned())


def test_catalog_commit_is_still_recorded_as_catalog_commit():
    """A table update from the catalog is still recorded as a catalog commit, not a discovery scan."""

    async def scenario(h: Harness) -> None:
        await h.start()
        await h.records(1)
        await h.signal(TableReconciliationSignal.TABLE_UPDATED)
        second = (await h.records(2))[1]
        assert second["wake_reasons"] == {"catalog_commit": 1}

    _run(scenario, script=lambda _: _planned())


def test_discovery_scan_starts_a_missing_workflow():
    """Signal-with-start on a discovery scan starts the missing workflow and records the scan."""

    async def scenario(h: Harness) -> None:
        await h.start(start_signal=TableReconciliationSignal.TABLE_SEEN)
        first = (await h.records(1))[0]
        assert first["wake_reasons"] == {"discovery_scan": 1}

    _run(scenario, script=lambda _: _planned())


def test_discovery_scan_after_stop_cancels_the_stop():
    """A discovery scan after ``stop`` supersedes it, the same as a catalog commit."""

    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.signal(TableReconciliationSignal.STOP)
        await h.signal(TableReconciliationSignal.TABLE_SEEN)
        assert (await h.settle())["stopping"] is False
        await h.complete_child(first)
        await h.plan_count(2)
        assert await h.status() == WorkflowExecutionStatus.RUNNING

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_reconciliation_passes_the_plan_deadline_to_the_run():
    """The run gets the attempt deadline the plan carries from the worker setting."""

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        assert (await h.child(run_id))["attempt_deadline_seconds"] == 120

    _run(scenario, script=lambda _: {**_planned(COMPACTION), "attempt_deadline_seconds": 120})


def test_reconciliation_defaults_the_deadline_for_old_plans():
    """A plan without a deadline, recorded before the setting existed, gives the run six hours per attempt."""

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        assert (await h.child(run_id))["attempt_deadline_seconds"] == 21600

    _run(scenario, script=lambda _: _planned(COMPACTION))


SHORT_DEADLINE_BUDGET = TableMaintenanceAttemptPolicy(
    attempt_deadline=timedelta(seconds=120)
).operation_worst_case() + (timedelta(hours=1))


def test_in_flight_bound_follows_the_plan_deadline():
    """A run planned with a short attempt deadline is given up after that deadline's worst case, not six hours'."""

    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.env.sleep(SHORT_DEADLINE_BUDGET - timedelta(minutes=1))
        assert (await h.settle())["in_flight_run_id"] == first
        await h.env.sleep(timedelta(minutes=2))
        await h.plan_count(2)
        assert await h.child_status(first) == WorkflowExecutionStatus.CANCELED

    _run(scenario, script=lambda _: {**_planned(COMPACTION, interval=10**6), "attempt_deadline_seconds": 120})


def test_reconciliation_passes_the_plan_max_attempts_to_the_run():
    """The run gets the attempts per operation the plan carries from the worker setting."""

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        assert (await h.child(run_id))["max_attempts"] == 5

    _run(scenario, script=lambda _: {**_planned(COMPACTION), "max_attempts": 5})


def test_reconciliation_defaults_the_max_attempts_for_old_plans():
    """A plan without max attempts, recorded before the setting existed, gives the run three attempts."""

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        assert (await h.child(run_id))["max_attempts"] == 3

    _run(scenario, script=lambda _: _planned(COMPACTION))


LONG_RETRY_BUDGET = TableMaintenanceAttemptPolicy(
    max_attempts=5, attempt_deadline=timedelta(seconds=120)
).operation_worst_case() + (timedelta(hours=1))


def test_in_flight_bound_follows_the_plan_max_attempts():
    """A run planned with more attempts is given up after their worst case, not after three attempts'."""

    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.env.sleep(LONG_RETRY_BUDGET - timedelta(minutes=1))
        assert (await h.settle())["in_flight_run_id"] == first
        await h.env.sleep(timedelta(minutes=2))
        await h.plan_count(2)
        assert await h.child_status(first) == WorkflowExecutionStatus.CANCELED

    _run(
        scenario,
        script=lambda _: {
            **_planned(COMPACTION, interval=10**6),
            "attempt_deadline_seconds": 120,
            "max_attempts": 5,
        },
    )


def test_carried_in_flight_run_keeps_its_attempt_deadline():
    """Continue-as-new carries the in-flight run's attempt deadline, so its bound does not change."""

    async def scenario(h: Harness) -> None:
        await h.start(
            start_signal=None,
            in_flight_run_id=GHOST_RUN_ID,
            in_flight_operation_count=1,
            in_flight_attempt_deadline_seconds=120,
        )
        state = await eventually(h.state, lambda s: s["in_flight_started_at"])
        await h.env.sleep(SHORT_DEADLINE_BUDGET - timedelta(minutes=1))
        assert (await h.settle())["in_flight_run_id"] == GHOST_RUN_ID
        await h.env.sleep(timedelta(minutes=2))
        await h.plan_count(1)
        await h.idle_after(state)

    _run(scenario, script=lambda _: _planned())


def test_in_flight_bound_includes_the_fencing_bound():
    """Each attempt's fencing bound is part of the budget: a run is still awaited past the bound without it."""

    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        without_fencing = 3 * (timedelta(hours=24) + timedelta(hours=6)) + timedelta(minutes=3) + timedelta(hours=1)
        await h.env.sleep(without_fencing + timedelta(minutes=30))
        assert (await h.settle())["in_flight_run_id"] == first
        assert len(h.plans.requests) == 1
        assert OPERATION_BUDGET == without_fencing + 3 * timedelta(minutes=15)

    _run(scenario, script=lambda _: _planned(COMPACTION, interval=10**6))


def test_reconciliation_passes_the_plan_queue_wait_limit_to_the_run():
    """The run gets the queue wait limit the plan carries from the worker setting."""

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        assert (await h.child(run_id))["queue_wait_limit_seconds"] == 600

    _run(scenario, script=lambda _: {**_planned(COMPACTION), "queue_wait_limit_seconds": 600})


def test_reconciliation_defaults_the_queue_wait_limit_for_old_plans():
    """A plan without a queue wait limit lets each attempt of the run wait a day in its queue."""

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        assert (await h.child(run_id))["queue_wait_limit_seconds"] == 86400

    _run(scenario, script=lambda _: _planned(COMPACTION))


SHORT_QUEUE_BUDGET = TableMaintenanceAttemptPolicy(
    attempt_deadline=timedelta(seconds=120), queue_wait_limit=timedelta(seconds=600)
).operation_worst_case() + (timedelta(hours=1))


def test_give_up_waits_for_queue_wait_plus_deadline():
    """A run is given up after every attempt's queue wait limit and deadline, as the plan carried them."""

    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        assert SHORT_QUEUE_BUDGET == 3 * timedelta(seconds=600 + 120 + 900) + timedelta(minutes=3, hours=1)
        await h.env.sleep(SHORT_QUEUE_BUDGET - timedelta(minutes=1))
        assert (await h.settle())["in_flight_run_id"] == first
        await h.env.sleep(timedelta(minutes=2))
        await h.plan_count(2)
        assert await h.child_status(first) == WorkflowExecutionStatus.CANCELED

    _run(
        scenario,
        script=lambda _: {
            **_planned(COMPACTION, interval=10**6),
            "attempt_deadline_seconds": 120,
            "queue_wait_limit_seconds": 600,
        },
    )


def test_carried_in_flight_run_keeps_its_queue_wait_limit():
    """Continue-as-new carries the in-flight run's queue wait limit, so its bound does not change."""

    async def scenario(h: Harness) -> None:
        await h.start(
            start_signal=None,
            in_flight_run_id=GHOST_RUN_ID,
            in_flight_operation_count=1,
            in_flight_attempt_deadline_seconds=120,
            in_flight_queue_wait_limit_seconds=600,
        )
        state = await eventually(h.state, lambda s: s["in_flight_started_at"])
        await h.env.sleep(SHORT_QUEUE_BUDGET - timedelta(minutes=1))
        assert (await h.settle())["in_flight_run_id"] == GHOST_RUN_ID
        await h.env.sleep(timedelta(minutes=2))
        await h.plan_count(1)
        await h.idle_after(state)

    _run(scenario, script=lambda _: _planned())


def test_continue_as_new_carries_the_in_flight_queue_wait_limit():
    """A carried run in flight across another continue-as-new is still given up on its queue wait limit."""

    async def scenario(h: Harness) -> None:
        handle = await h.start(
            start_signal=None,
            in_flight_run_id=GHOST_RUN_ID,
            in_flight_operation_count=1,
            in_flight_attempt_deadline_seconds=120,
            in_flight_queue_wait_limit_seconds=600,
            continue_as_new_after=2,
        )
        first_run = handle.result_run_id
        state = await eventually(h.state, lambda s: s["in_flight_started_at"])
        for _ in range(3):
            await h.signal(TableReconciliationSignal.POLICY_CHANGED)

        async def run_id_now() -> str | None:
            return (await h.client.get_workflow_handle(WORKFLOW_ID).describe()).run_id

        await eventually(run_id_now, lambda r: r != first_run)
        h.sent = 0
        assert (await h.settle())["in_flight_run_id"] == GHOST_RUN_ID
        await h.env.sleep(SHORT_QUEUE_BUDGET - timedelta(minutes=1))
        assert (await h.settle())["in_flight_run_id"] == GHOST_RUN_ID
        await h.env.sleep(timedelta(minutes=2))
        await h.plan_count(1)
        await h.idle_after(state)

    _run(scenario, script=lambda _: _planned())


FIXTURES = Path(__file__).parent / "fixtures"


def test_history_from_before_this_milestone_replays():
    """A reconciliation that started and finished a run under the code before this milestone replays unchanged."""

    async def go() -> None:
        history = WorkflowHistory.from_json(
            WORKFLOW_ID, (FIXTURES / "reconciliation_before_search_attributes.json").read_text()
        )
        await Replayer(workflows=[TableReconciliationWorkflow]).replay_workflow(history)

    asyncio.run(go())


def test_run_and_reconciliation_ids_survive_replay():
    """The run and reconciliation ids are minted deterministically: every workflow task replays the history.

    With no workflow cached, the worker rebuilds the workflow from its history on
    every task, so the plan, the child start and the record (each in a later task
    than the minting) see the ids minted again on replay; they agree, they have
    the ``mr-`` and ``rc-`` shapes, the history carries the patch marker that
    keeps older histories on their UUIDs, and it replays cleanly under the sandbox.
    """

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        record = (await h.records(1))[0]
        assert RUN_ID_SHAPE.fullmatch(run_id)
        assert RECONCILIATION_ID_SHAPE.fullmatch(record["reconciliation_id"])
        assert record["run_id"] == run_id
        assert (await h.child(run_id))["run_id"] == run_id
        history = await h.client.get_workflow_handle(WORKFLOW_ID).fetch_history()
        markers = [e.SerializeToString() for e in history.events if e.HasField("marker_recorded_event_attributes")]
        assert any(b"prefixed-run-and-reconciliation-ids" in m for m in markers)
        await Replayer(workflows=[TableReconciliationWorkflow]).replay_workflow(history)

    _run(scenario, script=lambda _: _planned(COMPACTION), max_cached_workflows=0)


# --- whole-table compaction, without compaction candidates ---


def test_plan_is_not_asked_for_a_run_id():
    """The plan claims nothing for the run it starts, so it is not told the run id."""

    async def scenario(h: Harness) -> None:
        await h.start()
        await h.in_flight()
        assert "run_id" not in h.plans.requests[0]

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_unstarted_run_releases_nothing(monkeypatch: pytest.MonkeyPatch):
    """A run that cannot be started is recorded as such and nothing is handed back, whatever its plan carried."""
    import temporalio.workflow

    async def failing_start(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        raise WorkflowAlreadyStartedError(kwargs["id"], args[0])

    monkeypatch.setattr(temporalio.workflow, "start_child_workflow", failing_start)

    async def scenario(h: Harness) -> None:
        await h.start()
        record = (await h.records(1))[0]
        assert record["run_start_failed"] is True
        await h.settle()
        assert await h.scheduled_activities() == ["plan_table_maintenance", "record_table_reconciliation"]

    _run(scenario, script=lambda _: _with_candidates(_planned(COMPACTION)), runner=UnsandboxedWorkflowRunner())


def test_stop_during_plan_releases_nothing():
    """A plan not started because the workflow is stopping is neither recorded nor handed back."""

    async def scenario(h: Harness) -> None:
        h.plans.gate = asyncio.Event()
        await h.start()
        await h.plan_count(1)
        await h.signal(TableReconciliationSignal.STOP)
        await eventually(h.state, lambda s: s["stopping"])
        h.plans.gate.set()
        await h.ended()
        assert await h.scheduled_activities() == ["plan_table_maintenance"]

    _run(scenario, script=lambda _: _with_candidates(_planned(COMPACTION)))


def test_next_plan_is_one_interval_on():
    """A plan's ``next_check_at`` is ignored: the next plan comes one reconcile interval later."""

    async def scenario(h: Harness) -> None:
        await h.start()
        first = (await h.plan_count(1))[0]
        await h.settle()
        await h.env.sleep(timedelta(seconds=100))
        assert len(h.plans.requests) == 1
        await h.env.sleep(timedelta(seconds=3600))
        second = (await h.plan_count(2))[1]
        gap = datetime.fromisoformat(second["now"]) - datetime.fromisoformat(first["now"])
        assert _within_a_second(gap, 3600)

    _run(scenario, script=_with_next_check(90))


def test_a_long_run_in_flight_still_blocks_planning():
    """However long a run takes, nothing is planned until it ends or is given up."""

    async def scenario(h: Harness) -> None:
        await h.start()
        run_id = await h.in_flight()
        await h.env.sleep(timedelta(hours=21))
        await h.signal(TableReconciliationSignal.TABLE_UPDATED)
        state = await h.settle()
        assert state["in_flight_run_id"] == run_id
        assert len(h.plans.requests) == 1

    _run(scenario, script=lambda _: _planned(COMPACTION, EXPIRE))


def test_history_from_before_whole_table_compaction_replays():
    """A history whose plans already carried candidates and a next check, under the code before, replays unchanged.

    Its first plan held every candidate until a next check, its second started a
    run that took a candidate, and its third was not started because the
    workflow was stopping: the new code neither looks again early nor releases.
    """

    async def go() -> None:
        history = WorkflowHistory.from_json(
            WORKFLOW_ID, (FIXTURES / "reconciliation_before_whole_table_compaction.json").read_text()
        )
        await Replayer(workflows=[TableReconciliationWorkflow]).replay_workflow(history)

    asyncio.run(go())


def _first_plan_with(flag: str, **stub: Any) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Plan a compaction carrying the stub flag ``flag`` (and ``stub``) first, then the manual operations asked for."""

    def answer(request: dict[str, Any]) -> dict[str, Any]:
        if request["manual_operations"]:
            return _planned(*request["manual_operations"])
        return {**_planned(COMPACTION), flag: True, **stub}

    return answer


def test_manual_trigger_raised_on_a_run_that_reports_meanwhile_is_planned_after_it(monkeypatch: pytest.MonkeyPatch):
    """A run that reports while its raise is on the way keeps the manual trigger pending, to be planned next.

    The raise's delivery is held, inside the workflow, until the run's report was handled, so the
    report always lands while the signal is awaited.
    """
    import temporalio.workflow

    real_handle = temporalio.workflow.get_external_workflow_handle

    class HeldRaiseHandle:
        def __init__(self, workflow_id: str) -> None:
            self._handle = real_handle(workflow_id)

        async def signal(self, name: str, arg: Any = None) -> None:  # noqa: ANN401
            await self._handle.signal(name, arg)
            if name == TableMaintenanceSignal.RAISE_PRIORITY:
                reconciliation = temporalio.workflow.instance()
                await temporalio.workflow.wait_condition(lambda: reconciliation.state()["in_flight_run_id"] is None)

        async def cancel(self) -> None:
            await self._handle.cancel()

    monkeypatch.setattr(temporalio.workflow, "get_external_workflow_handle", HeldRaiseHandle)

    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.signal(TableReconciliationSignal.TRIGGER_NOW, {"operations": [EXPIRE], "priority": "P1"})
        child = await h.child_handle(first)

        async def raises() -> list[str | None]:
            return await child.query("raises")

        await eventually(raises, lambda r: r == ["P1"])
        await h.complete_child(first)
        plan = (await h.plan_count(2))[1]
        assert (plan["manual_operations"], plan["manual_priority"]) == ([EXPIRE], "P1")
        assert (await h.records(2))[1]["wake_reasons"] == {"manual_run": 1, "previous_run_finished": 1}

    _run(
        scenario,
        script=lambda r: _planned(*(r["manual_operations"] or [COMPACTION])),
        runner=UnsandboxedWorkflowRunner(),
    )


def test_manual_trigger_whose_raise_the_run_left_unapplied_is_planned_after_it():
    """A raise the run received but never applied gives the manual trigger back once the run reports."""

    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.signal(TableReconciliationSignal.TRIGGER_NOW, {"operations": [EXPIRE], "priority": "P0"})
        child = await h.child_handle(first)

        async def raises() -> list[str | None]:
            return await child.query("raises")

        await eventually(raises, lambda r: r == ["P0"])
        state = await eventually(h.state, lambda s: s["pending_manual"] is None)
        assert (state["raised_manual"], state["raised_manual_priority"]) == ([EXPIRE], "P0")
        await h.complete_child(first)
        plan = (await h.plan_count(2))[1]
        assert (plan["manual_operations"], plan["manual_priority"]) == ([EXPIRE], "P0")
        second = (await h.records(2))[1]
        assert second["wake_reasons"] == {"manual_run": 1, "previous_run_finished": 1}
        assert second["run_start_failed"] is False
        run = await eventually(h.state, lambda s: s["in_flight_run_id"] not in (None, first))
        assert run["raised_manual"] is None
        assert (await h.child(run["in_flight_run_id"]))["trigger"] == "manual"

    _run(scenario, script=_first_plan_with("stub_leaves_raises_unapplied", stub_lingers_seconds=1))


def test_an_applied_raise_plans_no_manual_run_after_the_run():
    """A raise the run applied leaves nothing to plan for the trigger once the run reports."""

    async def scenario(h: Harness) -> None:
        await h.start_with_a_gone_child(raised_manual=[EXPIRE], raised_manual_priority="P0")
        await h.report_gone_child(unapplied_raise=False)
        plan = (await h.plan_count(1))[0]
        assert (plan["manual_operations"], plan["manual_priority"]) == (None, None)
        assert (await h.records(1))[0]["wake_reasons"] == {"previous_run_finished": 1}

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_continue_as_new_carries_the_raised_manual_trigger():
    """The trigger a raise consumed is carried through continue as new and given back if the raise went unapplied."""

    async def scenario(h: Harness) -> None:
        handle = await h.start_with_a_gone_child(
            continue_as_new_after=2, raised_manual=[EXPIRE], raised_manual_priority="P1"
        )
        first_run = handle.result_run_id
        await h.signal(TableReconciliationSignal.POLICY_CHANGED)
        await h.settle()
        for _ in range(2):
            await h.signal(TableReconciliationSignal.POLICY_CHANGED)

        async def run_id_now() -> str | None:
            return (await h.client.get_workflow_handle(WORKFLOW_ID).describe()).run_id

        await eventually(run_id_now, lambda r: r != first_run)
        state = await h.state()
        assert (state["raised_manual"], state["raised_manual_priority"]) == ([EXPIRE], "P1")
        await h.report_gone_child(unapplied_raise=True)
        plan = (await h.plan_count(1))[0]
        assert (plan["manual_operations"], plan["manual_priority"]) == ([EXPIRE], "P1")

    _run(scenario, script=lambda r: _planned(*(r["manual_operations"] or [COMPACTION])))


LINGERS = timedelta(minutes=3)


def test_next_run_waits_for_the_reporting_run_to_close():
    """A run that stays open a while after it reported is waited for; the next run then starts under the same id."""

    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.complete_child(first)
        await h.plan_count(2)
        state = await h.state()
        assert (state["closing_workflow_id"], len(h.recorder.records)) == (CHILD_ID, 1)
        await h.env.sleep(LINGERS + timedelta(seconds=30))
        second = await eventually(h.state, lambda s: s["in_flight_run_id"] not in (None, first))
        records = await h.records(2)
        assert [r["run_start_failed"] for r in records[:2]] == [False, False]
        assert (await h.child(second["in_flight_run_id"]))["run_id"] == second["in_flight_run_id"]
        assert second["closing_workflow_id"] is None

    _run(scenario, script=lambda _: {**_planned(COMPACTION), "stub_lingers_seconds": int(LINGERS.total_seconds())})


def test_stop_while_the_last_run_closes_starts_nothing():
    """A stop that arrives while the next run waits for the last one to close starts no run and records nothing."""

    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.complete_child(first)
        await h.plan_count(2)
        assert (await h.state())["closing_workflow_id"] == CHILD_ID
        await h.signal(TableReconciliationSignal.STOP)
        await eventually(h.state, lambda s: s["stopping"])
        await h.env.sleep(LINGERS + timedelta(seconds=30))
        await h.ended()
        assert len(h.recorder.records) == 1
        assert first in await h._started_children()  # noqa: SLF001
        assert len(await h._started_children()) == 1  # noqa: SLF001

    _run(scenario, script=lambda _: {**_planned(COMPACTION), "stub_lingers_seconds": int(LINGERS.total_seconds())})


def test_refused_start_keeps_the_manual_trigger_pending():
    """A manual trigger whose run could not be started stays pending for the next plan."""

    async def scenario(h: Harness) -> None:
        await h.client.start_workflow(
            TABLE_MAINTENANCE_WORKFLOW,
            TableMaintenanceWorkflowInput(
                run_id=OTHER_RUN_ID, table_uuid=UUID, parent_workflow_id="elsewhere", trigger="manual", plan=_planned()
            ),
            id=CHILD_ID,
            task_queue=TASK_QUEUE,
        )
        await h.start(start_signal=TableReconciliationSignal.TRIGGER_NOW)
        record = (await h.records(1))[0]
        assert record["run_start_failed"] is True
        state = await h.settle()
        assert state["pending_manual"] == []
        assert len(h.plans.requests) == 1

    _run(scenario, script=lambda _: _planned(COMPACTION))


def test_next_run_after_a_run_that_never_closes_is_refused():
    """A reported run still open past the closing bound is waited for no longer; its start is refused."""

    async def scenario(h: Harness) -> None:
        await h.start()
        first = await h.in_flight()
        await h.complete_child(first)
        await h.env.sleep(CLOSING_BOUND + timedelta(minutes=1))
        record = (await h.records(2))[1]
        assert record["run_start_failed"] is True
        assert (await h.settle())["closing_workflow_id"] is None

    _run(scenario, script=lambda _: {**_planned(COMPACTION), "stub_lingers_seconds": 7200})


def test_carried_closing_run_is_waited_for_before_the_next_plan():
    """A closing run carried through continue as new is looked up until it closed, then the next run starts."""

    async def scenario(h: Harness) -> None:
        await h.client.start_workflow(
            TABLE_MAINTENANCE_WORKFLOW,
            TableMaintenanceWorkflowInput(
                run_id=OTHER_RUN_ID, table_uuid=UUID, parent_workflow_id="elsewhere", trigger="manual", plan=_planned()
            ),
            id=CHILD_ID,
            task_queue=TASK_QUEUE,
        )
        await h.start(closing_workflow_id=CHILD_ID)
        await h.env.sleep(timedelta(minutes=1))
        assert h.recorder.records == []
        assert (await h.state())["closing_workflow_id"] == CHILD_ID
        await h.client.get_workflow_handle(CHILD_ID).signal("complete")
        await h.env.sleep(timedelta(seconds=30))
        record = (await h.records(1))[0]
        assert record["run_start_failed"] is False

    _run(scenario, script=lambda _: _planned(COMPACTION))
