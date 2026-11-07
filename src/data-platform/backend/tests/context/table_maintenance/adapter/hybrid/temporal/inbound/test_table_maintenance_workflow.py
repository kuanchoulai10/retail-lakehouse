"""Test the TableMaintenanceWorkflow on a time-skipping Temporal test server."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from temporalio.client import WorkflowFailureError
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.exceptions import CancelledError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    TABLE_MAINTENANCE_WORKFLOW,
    OperationResultSignal,
    TableMaintenanceSignal,
    TableMaintenanceWorkflowInput,
    table_maintenance_workflow_id,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance_admission import (
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW,
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID,
    AdmissionAcquireSignal,
    TableMaintenanceAdmissionSignal,
    TableMaintenanceAdmissionWorkflowInput,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities import (
    WorkflowSignalActivities,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import (
    TableMaintenanceAdmissionWorkflow,
    TableMaintenanceWorkflow,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.eventually import (
    eventually,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.parent_stub_workflow import (
    ParentStubWorkflow,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.scripted_maintenance_activities import (
    ScriptedMaintenanceActivities,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from temporalio.client import Client, WorkflowHandle

COMPACTION = "rewrite_data_files"
EXPIRE = "expire_snapshots"
RUN_ID = "run-1"
TABLE = "iceberg.e2e.t"
WORKFLOW_ID = table_maintenance_workflow_id(TABLE, RUN_ID)
PARENT_ID = "parent-1"
REAL_TIMEOUT_SECONDS = 20
ATTEMPT_DEADLINE_SECONDS = 21600


def _plan(*operations: str) -> dict:
    return {
        "status": "planned",
        "reason": None,
        "reconcile_interval_seconds": 3600,
        "table_name": TABLE,
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
    """Run the maintenance workflow against scripted activities and a parent stub."""

    env: WorkflowEnvironment
    client: Client
    queue: str
    fakes: ScriptedMaintenanceActivities

    async def run_maintenance(self, *operations: str, parent_id: str = PARENT_ID) -> None:
        """Start the workflow for the operations and wait for it to finish."""
        handle = await self.start_maintenance(*operations, parent_id=parent_id)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

    async def start_maintenance(
        self,
        *operations: str,
        parent_id: str = PARENT_ID,
        attempt_deadline_seconds: int = ATTEMPT_DEADLINE_SECONDS,
    ) -> WorkflowHandle:
        """Start the maintenance workflow for the operations and return its handle."""
        return await self.client.start_workflow(
            TABLE_MAINTENANCE_WORKFLOW,
            TableMaintenanceWorkflowInput(
                run_id=RUN_ID,
                table_uuid="u1",
                parent_workflow_id=parent_id,
                trigger="scheduled",
                plan=_plan(*operations),
                attempt_deadline_seconds=attempt_deadline_seconds,
            ),
            id=WORKFLOW_ID,
            task_queue=self.queue,
        )

    def recorded(self) -> list[tuple[str, int, bool, str | None]]:
        """Return the recorded results as operation, attempt, success and error tuples."""
        return [(r["operation"], r["attempt"], r["succeeded"], r["error"]) for r in self.fakes.records]

    def submit_times(self) -> list[datetime]:
        """Return the times the operations were submitted."""
        return [datetime.fromisoformat(s["now"]) for s in self.fakes.submits]

    async def parent_payloads(self) -> list[dict]:
        """Return the finished payloads the parent stub received."""
        return await self.client.get_workflow_handle(PARENT_ID).query("collected")

    async def admission_holders(self) -> dict:
        """Return the request ids that hold an admission slot."""
        handle = self.client.get_workflow_handle(TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID)
        return (await handle.query("state"))["holders"]


def _run(
    scenario: Callable[[Harness], Awaitable[None]],
    admission_limit: int = 1,
    lease_seconds: int = 30 * 24 * 3600,
) -> None:
    async def go() -> None:
        async with await WorkflowEnvironment.start_time_skipping() as env:
            queue = TASK_QUEUE
            fakes = ScriptedMaintenanceActivities(env.client)
            signals = WorkflowSignalActivities(
                env.client,
                admission_limit=admission_limit,
                admission_lease_seconds=lease_seconds,
            )
            async with (
                Worker(
                    env.client,
                    task_queue=queue,
                    workflows=[
                        TableMaintenanceWorkflow,
                        TableMaintenanceAdmissionWorkflow,
                    ],
                    activities=[
                        *fakes.all(),
                        signals.signal_admission_acquire,
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
                await env.client.start_workflow("ParentStub", id=PARENT_ID, task_queue=f"{queue}-stub")
                await scenario(Harness(env, env.client, queue, fakes))

    asyncio.run(go())


def test_operations_run_in_order_and_parent_signalled():
    """The operations run in order, each result is recorded and the parent is told when the run finishes."""

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
        assert h.fakes.created[0]["execution_ref"] == WORKFLOW_ID
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
        assert await h.parent_payloads() == [{"run_id": RUN_ID, "record_failures": 0}]
        assert await h.admission_holders() == {}

    _run(scenario)


def test_failed_operation_retried_three_attempts_total_then_next_operation_runs():
    """A failing operation is attempted three times with a backoff before the next operation runs."""

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
        assert await h.parent_payloads() == [{"run_id": RUN_ID, "record_failures": 0}]

    _run(scenario)


def test_stale_attempt_callback_is_ignored():
    """A result callback for an earlier attempt is ignored."""

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
    """Polling a job whose driver crashed records the attempt as failed."""

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
    """Polling records a failure for a missing job and a completed job that never called back."""

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
        assert h.fakes.records[1]["metrics"] == {"completed_without_callback": 1}
        completed_polls = h.fakes.status_calls.count(f"{RUN_ID}-{COMPACTION}-2")
        assert completed_polls == 5

    _run(scenario)


def test_admission_released_when_submit_activity_fails():
    """The admission slot is released and the job deleted when the submit activity fails."""

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
        assert h.fakes.deletes == [
            f"{RUN_ID}-{COMPACTION}-1",
            f"{RUN_ID}-{COMPACTION}-2",
        ]
        assert await h.admission_holders() == {}

    _run(scenario, admission_limit=1)


def test_missing_parent_does_not_fail_the_workflow():
    """A missing parent workflow does not fail the maintenance run."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 1): [(1, True, None)]}
        await h.run_maintenance(COMPACTION, parent_id="no-such-parent")
        assert h.recorded() == [(COMPACTION, 1, True, None)]

    _run(scenario)


def test_completed_window_restarts_when_state_leaves_completed():
    """The wait for a callback after completion restarts when the job state leaves completed."""

    async def scenario(h: Harness) -> None:
        completed = {"state": "COMPLETED", "error": None}
        running = {"state": "RUNNING", "error": None}
        h.fakes.states[f"{RUN_ID}-{COMPACTION}-1"] = [completed, running, completed]
        await h.run_maintenance(COMPACTION)

        assert h.recorded() == [(COMPACTION, 1, True, None)]
        assert h.fakes.status_calls.count(f"{RUN_ID}-{COMPACTION}-1") == 7

    _run(scenario)


def test_attempt_times_out_after_deadline():
    """An attempt that exceeds its deadline is recorded as failed and its job is deleted."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}
        await h.run_maintenance(COMPACTION)

        assert h.recorded() == [
            (COMPACTION, 1, False, "spark job timed out"),
            (COMPACTION, 2, True, None),
        ]
        times = h.submit_times()
        deadline = timedelta(seconds=ATTEMPT_DEADLINE_SECONDS)
        assert deadline <= times[1] - times[0] < deadline + timedelta(seconds=120)
        assert h.fakes.deletes == [
            f"{RUN_ID}-{COMPACTION}-1",
            f"{RUN_ID}-{COMPACTION}-2",
        ]

    _run(scenario)


def test_poll_interval_backs_off_after_ten_minutes():
    """Status polls are under a minute apart for the first ten minutes and at least five minutes apart later."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}
        await h.run_maintenance(COMPACTION)

        app = f"{RUN_ID}-{COMPACTION}-1"
        submitted = h.submit_times()[0]
        polls = [t for t, name in zip(h.fakes.status_times, h.fakes.status_calls, strict=True) if name == app]
        first_hour = [t for t in polls if t - submitted < timedelta(hours=1, seconds=30)]
        assert len(first_hour) == 20 + 10
        gaps = [b - a for a, b in zip(polls, polls[1:], strict=False)]
        assert all(g < timedelta(seconds=60) for g in gaps[:19])
        assert all(g >= timedelta(minutes=5) for g in gaps[20:])
        assert len(polls) < 100

    _run(scenario)


def test_cancelled_workflow_records_releases_deletes_and_notifies():
    """A cancelled workflow records the cancellation, releases its slot, deletes the job and notifies the parent."""

    async def scenario(h: Harness) -> None:
        handle = await h.start_maintenance(COMPACTION, EXPIRE)
        await eventually(lambda: _value(len(h.fakes.submits)), lambda n: n == 1)
        await handle.cancel()
        with pytest.raises(WorkflowFailureError) as caught:
            await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)
        assert isinstance(caught.value.cause, CancelledError)

        assert h.recorded() == [(COMPACTION, 1, False, "cancelled")]
        assert h.fakes.deletes == [f"{RUN_ID}-{COMPACTION}-1"]
        assert await h.parent_payloads() == [{"run_id": RUN_ID, "record_failures": 0}]
        assert await h.admission_holders() == {}

    _run(scenario)


def test_late_grant_for_another_request_is_released_at_once():
    """A grant that arrives for another request is released immediately."""

    async def scenario(h: Harness) -> None:
        h.fakes.create_gate = asyncio.Event()
        h.fakes.callbacks = {(COMPACTION, 1): [(1, True, None)]}
        handle = await h.start_maintenance(COMPACTION)
        await eventually(lambda: _value(len(h.fakes.created)), lambda n: n == 1)
        await h.client.start_workflow(
            TABLE_MAINTENANCE_ADMISSION_WORKFLOW,
            TableMaintenanceAdmissionWorkflowInput(limit=1, lease_seconds=30 * 24 * 3600),
            id=TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID,
            task_queue=h.queue,
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
            start_signal=TableMaintenanceAdmissionSignal.ACQUIRE,
            start_signal_args=[AdmissionAcquireSignal("stray", handle.id)],
        )
        await eventually(h.admission_holders, lambda holders: holders == {})
        h.fakes.create_gate.set()
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)
        assert h.recorded() == [(COMPACTION, 1, True, None)]

    _run(scenario, admission_limit=1)


def test_record_failures_are_counted_in_the_parent_payload():
    """Failures to record a result are counted in the payload sent to the parent."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {
            (COMPACTION, 1): [(1, True, None)],
            (EXPIRE, 1): [(1, True, None)],
        }
        h.fakes.record_errors = {(COMPACTION, 1)}
        await h.run_maintenance(COMPACTION, EXPIRE)

        assert [(r["operation"], r["attempt"]) for r in h.fakes.records] == [
            (COMPACTION, 1),
            (EXPIRE, 1),
        ]
        assert await h.parent_payloads() == [{"run_id": RUN_ID, "record_failures": 1}]

    _run(scenario)


async def _value(value: object) -> object:
    return value


async def _cancel_while_blocked(
    h: Harness,
    gate: asyncio.Event,
    blocked: Callable[[], bool],
    advance: timedelta = timedelta(0),
) -> None:
    handle = await h.start_maintenance(COMPACTION, EXPIRE)
    try:
        await eventually(lambda: _value(len(h.fakes.submits)), lambda n: n == 1)
        if advance:
            await h.env.sleep(advance)
        await eventually(lambda: _value(blocked()), bool)
        await handle.cancel()
        with pytest.raises(WorkflowFailureError) as caught:
            await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)
    finally:
        gate.set()
    assert isinstance(caught.value.cause, CancelledError)
    assert h.recorded() == [(COMPACTION, 1, False, "cancelled")]
    assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [(COMPACTION, 1)]
    assert h.fakes.deletes == [f"{RUN_ID}-{COMPACTION}-1"]
    assert await h.parent_payloads() == [{"run_id": RUN_ID, "record_failures": 0}]
    assert await h.admission_holders() == {}


def test_cancel_during_status_poll_activity_cancels_the_workflow():
    """A cancel while a status poll is running cancels the workflow."""

    async def scenario(h: Harness) -> None:
        gate = h.fakes.status_gate = asyncio.Event()
        await _cancel_while_blocked(
            h,
            gate,
            lambda: len(h.fakes.status_calls) == 1,
            advance=timedelta(seconds=31),
        )
        assert h.fakes.status_calls == [f"{RUN_ID}-{COMPACTION}-1"]

    _run(scenario)


def test_cancel_during_submit_activity_cancels_the_workflow():
    """A cancel while the submit activity is running cancels the workflow."""

    async def scenario(h: Harness) -> None:
        gate = h.fakes.submit_gate = asyncio.Event()
        await _cancel_while_blocked(h, gate, lambda: len(h.fakes.submits) == 1)

    _run(scenario)


def test_result_arriving_during_last_poll_before_deadline_wins():
    """A result that arrives during the last poll before the deadline counts as the outcome of the attempt."""

    async def scenario(h: Harness) -> None:
        deadline = timedelta(seconds=100)
        app = f"{RUN_ID}-{COMPACTION}-1"
        signalled: list[datetime] = []

        async def hook(app_name: str, scheduled: datetime) -> None:
            # The poll at 90 s, the last before the 100 s deadline, receives the
            # callback and returns only after the deadline has passed.
            submitted = h.submit_times()[0]
            if app_name != app or signalled or scheduled - submitted < timedelta(seconds=85):
                return
            signalled.append(scheduled)
            await h.client.get_workflow_handle(WORKFLOW_ID).signal(
                TableMaintenanceSignal.OPERATION_RESULT,
                OperationResultSignal(RUN_ID, COMPACTION, 1, True, {"files": 7}, None),
            )
            await h.env.sleep(timedelta(seconds=30))

        h.fakes.status_hook = hook
        handle = await h.start_maintenance(COMPACTION, attempt_deadline_seconds=int(deadline.total_seconds()))
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert h.recorded() == [(COMPACTION, 1, True, None)]
        assert h.fakes.records[0]["metrics"] == {"files": 7}
        recorded_at = datetime.fromisoformat(h.fakes.records[0]["now"])
        assert recorded_at >= h.submit_times()[0] + deadline
        assert len(h.fakes.submits) == 1
        assert len(signalled) == 1

    _run(scenario)
