"""Test the MaintenanceWorkflow on a time-skipping Temporal test server."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from temporalio.testing import WorkflowEnvironment
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from adapter.inbound.temporal.activities import WorkflowSignalActivities
from adapter.inbound.temporal.workflows import (
    CapacityLimiterWorkflow,
    MaintenanceWorkflow,
)
from adapter.temporal_contracts.maintenance_workflow_input import (
    MaintenanceWorkflowInput,
)
from adapter.temporal_contracts.workflow_names import MAINTENANCE_WORKFLOW
from application.domain.model.maintenance.workflow_ids import (
    CAPACITY_WORKFLOW_ID,
    maintenance_workflow_id,
)
from tests.adapter.inbound.temporal.parent_stub_workflow import ParentStubWorkflow
from tests.adapter.inbound.temporal.scripted_maintenance_activities import (
    ScriptedMaintenanceActivities,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from temporalio.client import Client

COMPACTION = "rewrite_data_files"
EXPIRE = "expire_snapshots"
RUN_ID = "run-1"
PARENT_ID = "parent-1"
REAL_TIMEOUT_SECONDS = 20


def _plan(*operations: str) -> dict:
    return {
        "status": "planned",
        "reason": None,
        "reconcile_interval_seconds": 3600,
        "operations": [
            {
                "operation": op,
                "filters": [{"spec_id": 0, "where": f"{op} = 1"}],
                "procedure_args": {"op": op},
            }
            for op in operations
        ],
    }


@dataclass
class Harness:
    env: WorkflowEnvironment
    client: Client
    queue: str
    fakes: ScriptedMaintenanceActivities

    async def run_maintenance(
        self, *operations: str, parent_id: str = PARENT_ID
    ) -> None:
        handle = await self.client.start_workflow(
            MAINTENANCE_WORKFLOW,
            MaintenanceWorkflowInput(
                run_id=RUN_ID,
                table_uuid="u1",
                parent_workflow_id=parent_id,
                trigger="scheduled",
                plan=_plan(*operations),
            ),
            id=maintenance_workflow_id(RUN_ID),
            task_queue=self.queue,
        )
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

    def recorded(self) -> list[tuple[str, int, bool, str | None]]:
        return [
            (r["operation"], r["attempt"], r["succeeded"], r["error"])
            for r in self.fakes.records
        ]

    def submit_times(self) -> list[datetime]:
        return [datetime.fromisoformat(s["now"]) for s in self.fakes.submits]

    async def limiter_holders(self) -> dict:
        handle = self.client.get_workflow_handle(CAPACITY_WORKFLOW_ID)
        return (await handle.query("state"))["holders"]


def _run(
    scenario: Callable[[Harness], Awaitable[None]],
    capacity_limit: int = 1,
    lease_seconds: int = 30 * 24 * 3600,
) -> None:
    async def go() -> None:
        async with await WorkflowEnvironment.start_time_skipping() as env:
            queue = f"q-{uuid.uuid4()}"
            fakes = ScriptedMaintenanceActivities(env.client)
            signals = WorkflowSignalActivities(
                env.client,
                capacity_limit=capacity_limit,
                capacity_lease_seconds=lease_seconds,
                task_queue=queue,
            )
            async with (
                Worker(
                    env.client,
                    task_queue=queue,
                    workflows=[MaintenanceWorkflow, CapacityLimiterWorkflow],
                    activities=[
                        *fakes.all(),
                        signals.signal_capacity_acquire,
                        signals.signal_parent,
                    ],
                ),
                Worker(
                    env.client,
                    task_queue=f"{queue}-stub",
                    workflows=[ParentStubWorkflow],
                    workflow_runner=UnsandboxedWorkflowRunner(),
                ),
            ):
                await env.client.start_workflow(
                    "ParentStub", id=PARENT_ID, task_queue=f"{queue}-stub"
                )
                await scenario(Harness(env, env.client, queue, fakes))

    asyncio.run(go())


def test_operations_run_in_order_and_parent_signalled():
    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {
            (COMPACTION, 1): [(1, True, None)],
            (EXPIRE, 1): [(1, True, None)],
        }
        await h.run_maintenance(COMPACTION, EXPIRE)

        assert h.fakes.created[0]["run_id"] == RUN_ID
        assert h.fakes.created[0]["table_uuid"] == "u1"
        assert h.fakes.created[0]["trigger"] == "scheduled"
        assert h.fakes.created[0]["operations"] == [COMPACTION, EXPIRE]
        first = h.fakes.submits[0]
        assert first["filters"] == [{"spec_id": 0, "where": f"{COMPACTION} = 1"}]
        assert first["procedure_args"] == {"op": COMPACTION}
        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [
            (COMPACTION, 1),
            (EXPIRE, 1),
        ]
        assert h.recorded() == [(COMPACTION, 1, True, None), (EXPIRE, 1, True, None)]
        assert h.fakes.records[0]["metrics"] == {"files": 1}
        assert h.fakes.deletes == [
            f"{RUN_ID}-{COMPACTION}-1",
            f"{RUN_ID}-{EXPIRE}-1",
        ]
        parent = h.client.get_workflow_handle(PARENT_ID)
        assert await parent.query("collected") == [RUN_ID]
        assert await h.limiter_holders() == {}

    _run(scenario)


def test_failed_operation_retried_three_attempts_total_then_next_operation_runs():
    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {
            (COMPACTION, 1): [(1, False, "boom-1")],
            (COMPACTION, 2): [(2, False, "boom-2")],
            (COMPACTION, 3): [(3, False, "boom-3")],
            (EXPIRE, 1): [(1, True, None)],
        }
        await h.run_maintenance(COMPACTION, EXPIRE)

        assert h.recorded() == [
            (COMPACTION, 1, False, "boom-1"),
            (COMPACTION, 2, False, "boom-2"),
            (COMPACTION, 3, False, "boom-3"),
            (EXPIRE, 1, True, None),
        ]
        times = h.submit_times()
        assert times[1] - times[0] >= timedelta(seconds=60)
        assert times[1] - times[0] < timedelta(seconds=120)
        assert times[2] - times[1] >= timedelta(seconds=120)
        assert times[2] - times[1] < timedelta(seconds=180)
        assert len(h.fakes.deletes) == 4
        parent = h.client.get_workflow_handle(PARENT_ID)
        assert await parent.query("collected") == [RUN_ID]

    _run(scenario)


def test_stale_attempt_callback_is_ignored():
    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {
            (COMPACTION, 1): [(1, False, "boom-1")],
            (COMPACTION, 2): [(1, True, None)],
            (COMPACTION, 3): [(3, True, None)],
        }
        h.fakes.states[f"{RUN_ID}-{COMPACTION}-2"] = {"state": "FAILED", "error": None}
        await h.run_maintenance(COMPACTION)

        assert h.recorded() == [
            (COMPACTION, 1, False, "boom-1"),
            (COMPACTION, 2, False, "spark job failed"),
            (COMPACTION, 3, True, None),
        ]
        assert h.fakes.status_calls == [f"{RUN_ID}-{COMPACTION}-2"]

    _run(scenario)


def test_polling_detects_crashed_driver():
    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 3): [(3, True, None)]}
        h.fakes.states[f"{RUN_ID}-{COMPACTION}-1"] = {"state": "FAILED", "error": None}
        h.fakes.states[f"{RUN_ID}-{COMPACTION}-2"] = {"state": "FAILED", "error": "oom"}
        await h.run_maintenance(COMPACTION)

        assert h.recorded() == [
            (COMPACTION, 1, False, "spark job failed"),
            (COMPACTION, 2, False, "oom"),
            (COMPACTION, 3, True, None),
        ]

    _run(scenario)


def test_polling_detects_missing_job_and_completed_without_callback():
    async def scenario(h: Harness) -> None:
        h.fakes.states[f"{RUN_ID}-{COMPACTION}-1"] = {
            "state": "NOT_FOUND",
            "error": None,
        }
        h.fakes.states[f"{RUN_ID}-{COMPACTION}-2"] = {
            "state": "COMPLETED",
            "error": None,
        }
        await h.run_maintenance(COMPACTION)

        assert h.recorded() == [
            (COMPACTION, 1, False, "spark job missing"),
            (COMPACTION, 2, True, None),
        ]
        assert h.fakes.records[1]["metrics"] == {}
        completed_polls = h.fakes.status_calls.count(f"{RUN_ID}-{COMPACTION}-2")
        assert completed_polls == 5

    _run(scenario)


def test_capacity_released_when_submit_activity_fails():
    async def scenario(h: Harness) -> None:
        h.fakes.submit_errors = {(COMPACTION, 1): "attempt already started"}
        h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}
        await h.run_maintenance(COMPACTION)

        assert h.recorded() == [
            (COMPACTION, 1, False, "submit failed: attempt already started"),
            (COMPACTION, 2, True, None),
        ]
        times = h.submit_times()
        assert times[1] - times[0] < timedelta(seconds=120)
        assert h.fakes.deletes == [f"{RUN_ID}-{COMPACTION}-2"]
        assert await h.limiter_holders() == {}

    _run(scenario, capacity_limit=1)


def test_missing_parent_does_not_fail_the_workflow():
    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 1): [(1, True, None)]}
        await h.run_maintenance(COMPACTION, parent_id="no-such-parent")
        assert h.recorded() == [(COMPACTION, 1, True, None)]

    _run(scenario)
