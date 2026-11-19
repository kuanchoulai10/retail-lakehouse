"""Test the TableMaintenanceWorkflow on a time-skipping Temporal test server."""

from __future__ import annotations

import asyncio
import itertools
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from temporalio import activity
from temporalio.client import WorkflowFailureError, WorkflowHistory
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.exceptions import ApplicationError, CancelledError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer, UnsandboxedWorkflowRunner, Worker

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    TABLE_MAINTENANCE_WORKFLOW,
    OperationResultSignal,
    TableMaintenanceActivity,
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
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.table_maintenance_activities_with_fakes import (  # noqa: E501
    table_maintenance_activities_with_fakes,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from temporalio.client import Client, WorkflowHandle

COMPACTION = "rewrite_data_files"
EXPIRE = "expire_snapshots"
RUN_ID = "mr-00000000000000000000000001"
TABLE = "iceberg.e2e.t"
WORKFLOW_ID = table_maintenance_workflow_id(TABLE, RUN_ID)
PARENT_ID = "parent-1"
REAL_TIMEOUT_SECONDS = 60
ATTEMPT_DEADLINE_SECONDS = 21600
PLANNED_POLICY = ("nightly", 2, {"type": "namespace", "path": ["iceberg", "sales"]})


def _plan(*operations: str, start_size: str | None = None) -> dict:
    sized = {} if start_size is None else {"start_size": start_size}
    return {
        "status": "planned",
        "reason": None,
        "reconcile_interval_seconds": 3600,
        "table_name": TABLE,
        "policy_name": PLANNED_POLICY[0],
        "policy_version": PLANNED_POLICY[1],
        "policy_target": PLANNED_POLICY[2],
        "operations": [
            {
                "operation": op,
                "filters": [{"spec_id": 0, "where": f"{op} = 1"}],
                "procedure_args": {"op": op},
                **sized,
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

    async def run_maintenance(
        self,
        *operations: str,
        parent_id: str = PARENT_ID,
        start_size: str | None = None,
        plan: dict | None = None,
    ) -> None:
        """Start the workflow for the operations (or ``plan``) and wait for it to finish."""
        handle = await self.start_maintenance(*operations, parent_id=parent_id, start_size=start_size, plan=plan)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

    async def start_maintenance(
        self,
        *operations: str,
        parent_id: str = PARENT_ID,
        attempt_deadline_seconds: int = ATTEMPT_DEADLINE_SECONDS,
        max_attempts: int = 3,
        start_size: str | None = None,
        plan: dict | None = None,
    ) -> WorkflowHandle:
        """Start the maintenance workflow for the operations, or for ``plan``, and return its handle."""
        return await self.client.start_workflow(
            TABLE_MAINTENANCE_WORKFLOW,
            TableMaintenanceWorkflowInput(
                run_id=RUN_ID,
                table_uuid="u1",
                parent_workflow_id=parent_id,
                trigger="scheduled",
                plan=plan or _plan(*operations, start_size=start_size),
                attempt_deadline_seconds=attempt_deadline_seconds,
                max_attempts=max_attempts,
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

    async def commands(self) -> list[tuple[str, datetime]]:
        """Return the activities and external signals the workflow issued, in order, with their times.

        An activity appears by its name, a signal to another workflow as ``signal:<name>``.
        """
        history = await self.client.get_workflow_handle(WORKFLOW_ID).fetch_history()
        issued: list[tuple[str, datetime]] = []
        for event in history.events:
            at = event.event_time.ToDatetime(tzinfo=UTC)
            if event.HasField("activity_task_scheduled_event_attributes"):
                issued.append((event.activity_task_scheduled_event_attributes.activity_type.name, at))
            elif event.HasField("signal_external_workflow_execution_initiated_event_attributes"):
                name = event.signal_external_workflow_execution_initiated_event_attributes.signal_name
                issued.append((f"signal:{name}", at))
        return issued

    async def admission_holders(self) -> dict:
        """Return the request ids that hold an admission slot."""
        handle = self.client.get_workflow_handle(TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID)
        return (await handle.query("state"))["holders"]


def _run(
    scenario: Callable[[Harness], Awaitable[None]],
    admission_limit: int = 1,
    lease_seconds: int = 30 * 24 * 3600,
    failing_acquires: frozenset[str] = frozenset(),
) -> None:
    """Run ``scenario`` against the workflows on a time-skipping server.

    The admission acquire is the real signal activity, except that an acquire for a request id in
    ``failing_acquires`` fails non-retryably, as when the admission workflow cannot be reached.
    """

    async def go() -> None:
        async with await WorkflowEnvironment.start_time_skipping() as env:
            queue = TASK_QUEUE
            fakes = ScriptedMaintenanceActivities(env.client)
            signals = table_maintenance_activities_with_fakes(
                client=env.client,
                admission_limit=admission_limit,
                admission_lease_seconds=lease_seconds,
            )

            @activity.defn(name=TableMaintenanceActivity.SIGNAL_ADMISSION_ACQUIRE)
            async def signal_admission_acquire(request: dict) -> None:
                if request["request_id"] in failing_acquires:
                    raise ApplicationError("admission workflow unavailable", type="RuntimeError", non_retryable=True)
                await signals.signal_admission_acquire(request)

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
                        signal_admission_acquire,
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


def test_the_input_sets_how_many_attempts_an_operation_gets():
    """An operation is attempted as often as the run's max attempts say, then the next operation runs."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {
            (COMPACTION, 1): [(1, False, "boom-1")],
            (COMPACTION, 2): [(2, False, "boom-2")],
            (COMPACTION, 3): [(3, False, "boom-3")],
            (COMPACTION, 4): [(4, False, "boom-4")],
            (EXPIRE, 1): [(1, True, None)],
        }
        handle = await h.start_maintenance(COMPACTION, EXPIRE, max_attempts=2)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert h.recorded() == [
            (COMPACTION, 1, False, "boom-1"),
            (COMPACTION, 2, False, "boom-2"),
            (EXPIRE, 1, True, None),
        ]
        assert all(r["max_attempts"] == 2 for r in h.fakes.records)

    _run(scenario)


def test_more_attempts_than_backoffs_sleep_the_last_backoff_again():
    """With four attempts the third and fourth failures sleep the last listed backoff, 120 s."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, n): [(n, False, f"boom-{n}")] for n in (1, 2, 3, 4)}
        handle = await h.start_maintenance(COMPACTION, max_attempts=4)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert [r[1] for r in h.recorded()] == [1, 2, 3, 4]
        times = h.submit_times()
        assert timedelta(seconds=120) <= times[3] - times[2] < timedelta(seconds=180)

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
    """A timed-out attempt is recorded as failed; its job is deleted when it is fenced and again at the end."""

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
        cancelled: list[bool] = []
        _cancel_on_the_first_status_poll(h, cancelled)
        handle = await h.start_maintenance(COMPACTION, EXPIRE)
        with pytest.raises(WorkflowFailureError) as caught:
            await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)
        assert isinstance(caught.value.cause, CancelledError)
        assert cancelled == [True]

        assert h.recorded() == [(COMPACTION, 1, False, "cancelled")]
        assert set(h.fakes.deletes) == {f"{RUN_ID}-{COMPACTION}-1"}
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
    assert set(h.fakes.deletes) == {f"{RUN_ID}-{COMPACTION}-1"}
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


FENCE_DEADLINE_SECONDS = 300
UNCONFIRMED_ERROR = "spark job timed out; its pods were still running 15 minutes after the timeout"
FIRST = f"{RUN_ID}-{COMPACTION}-1"


def _names(commands: list[tuple[str, datetime]]) -> list[str]:
    return [name for name, _ in commands]


def _first_after(commands: list[tuple[str, datetime]], name: str, start: int) -> int:
    return next(i for i in range(start, len(commands)) if commands[i][0] == name)


def test_timed_out_attempt_deletes_the_job_before_release():
    """A timed-out attempt deletes its job and confirms its pods are gone before its slot is released and retried."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}
        handle = await h.start_maintenance(COMPACTION, attempt_deadline_seconds=FENCE_DEADLINE_SECONDS)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        commands = await h.commands()
        names = _names(commands)
        delete = names.index("delete_maintenance_job")
        pods = _first_after(commands, "get_maintenance_job_pods", delete)
        release = _first_after(commands, "signal:release", pods)
        second_submit = _first_after(commands, "submit_maintenance_operation", release)
        assert names.index("submit_maintenance_operation") < delete < pods < release < second_submit
        assert "signal:release" not in names[:pods]
        assert h.recorded() == [(COMPACTION, 1, False, "spark job timed out"), (COMPACTION, 2, True, None)]
        assert h.fakes.pods_calls == [FIRST]

    _run(scenario)


def test_next_attempt_is_not_submitted_while_pods_are_live():
    """The next attempt is submitted only after a poll finds the timed-out attempt's pods gone."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}
        h.fakes.pods_live_polls[FIRST] = 3
        handle = await h.start_maintenance(COMPACTION, attempt_deadline_seconds=FENCE_DEADLINE_SECONDS)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert h.fakes.pods_calls == [FIRST] * 4
        gaps = [b - a for a, b in itertools.pairwise(h.fakes.pods_times)]
        assert all(timedelta(seconds=30) <= g < timedelta(seconds=60) for g in gaps)
        assert h.submit_times()[1] > h.fakes.pods_times[-1]
        assert h.recorded() == [(COMPACTION, 1, False, "spark job timed out"), (COMPACTION, 2, True, None)]

    _run(scenario)


def test_fencing_renews_the_admission_lease_while_waiting():
    """While the pods of a timed-out attempt stay live, the attempt keeps renewing its admission lease."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}
        h.fakes.pods_live_for[FIRST] = timedelta(minutes=12)
        handle = await h.start_maintenance(COMPACTION, attempt_deadline_seconds=FENCE_DEADLINE_SECONDS)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        commands = await h.commands()
        names = _names(commands)
        delete = names.index("delete_maintenance_job")
        release = _first_after(commands, "signal:release", delete)
        renews = [at for name, at in commands[delete:release] if name == "signal:renew"]
        assert len(renews) >= 2
        assert all(b - a <= timedelta(minutes=5, seconds=30) for a, b in itertools.pairwise(renews))

    _run(scenario, lease_seconds=FENCE_DEADLINE_SECONDS + 15 * 60)


def test_fencing_renews_the_lease_before_it_deletes_the_job():
    """The first thing a timed-out attempt does is renew its lease, then it deletes its job."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}
        handle = await h.start_maintenance(COMPACTION, attempt_deadline_seconds=FENCE_DEADLINE_SECONDS)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        names = _names(await h.commands())
        assert names.index("signal:renew") < names.index("delete_maintenance_job")

    _run(scenario)


def test_failed_delete_is_retried_on_every_fencing_poll():
    """A delete that fails is tried again on the next poll, and the pods are checked only once it succeeded."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}
        h.fakes.delete_failures[FIRST] = 3
        handle = await h.start_maintenance(COMPACTION, attempt_deadline_seconds=FENCE_DEADLINE_SECONDS)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        commands = await h.commands()
        deletes = [at for name, at in commands if name == "delete_maintenance_job"][:4]
        assert len(deletes) == 4
        assert all(timedelta(seconds=30) <= b - a < timedelta(seconds=60) for a, b in itertools.pairwise(deletes))
        assert h.fakes.pods_times[0] >= deletes[3]
        assert h.recorded() == [(COMPACTION, 1, False, "spark job timed out"), (COMPACTION, 2, True, None)]

    _run(scenario)


def test_job_that_cannot_be_deleted_fails_the_operation_and_keeps_the_slot():
    """A job still not deleted 15 minutes after the timeout fails the operation; the slot waits for the delete."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(EXPIRE, 1): [(1, True, None)]}
        h.fakes.delete_failures[FIRST] = 40
        handle = await h.start_maintenance(COMPACTION, EXPIRE, attempt_deadline_seconds=FENCE_DEADLINE_SECONDS)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        undeletable = "spark job timed out; its job could still not be deleted 15 minutes after the timeout"
        assert h.recorded() == [(COMPACTION, 1, False, undeletable), (EXPIRE, 1, True, None)]
        assert h.fakes.pods_times[0] >= h.fakes.delete_times[FIRST]
        commands = await h.commands()
        release = _first_after(commands, "signal:release", _names(commands).index("delete_maintenance_job"))
        assert commands[release][1] >= h.fakes.delete_times[FIRST]

    _run(scenario)


def test_missing_job_is_fenced_before_its_slot_is_released():
    """A job that went missing has its pods waited for, with the lease renewed, before the slot is released."""

    async def scenario(h: Harness) -> None:
        h.fakes.states[FIRST] = {"state": "NOT_FOUND", "error": None}
        h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}
        h.fakes.pods_live_polls[FIRST] = 3
        await h.run_maintenance(COMPACTION)

        commands = await h.commands()
        names = _names(commands)
        status = names.index("get_maintenance_job_status")
        renew = _first_after(commands, "signal:renew", status)
        delete = _first_after(commands, "delete_maintenance_job", renew)
        release = _first_after(commands, "signal:release", delete)
        assert h.fakes.pods_calls == [FIRST] * 4
        assert commands[release][1] >= h.fakes.pods_times[-1]
        assert h.submit_times()[1] > h.fakes.pods_times[-1]
        assert h.recorded() == [(COMPACTION, 1, False, "spark job missing"), (COMPACTION, 2, True, None)]

    _run(scenario)


def test_missing_job_whose_pods_stay_fails_the_operation_and_keeps_the_slot():
    """Pods of a missing job still live 15 minutes later fail the operation; the slot waits for them."""

    async def scenario(h: Harness) -> None:
        h.fakes.states[FIRST] = {"state": "NOT_FOUND", "error": None}
        h.fakes.callbacks = {(EXPIRE, 1): [(1, True, None)]}
        h.fakes.pods_live_for[FIRST] = timedelta(minutes=20)
        await h.run_maintenance(COMPACTION, EXPIRE)

        stuck = "spark job missing; its pods were still running 15 minutes after the job went missing"
        assert h.recorded() == [(COMPACTION, 1, False, stuck), (EXPIRE, 1, True, None)]
        commands = await h.commands()
        release = _first_after(commands, "signal:release", _names(commands).index("delete_maintenance_job"))
        assert commands[release][1] - h.fakes.delete_times[FIRST] >= timedelta(minutes=20)

    _run(scenario)


async def _cancel_requested_for_an_activity(h: Harness) -> bool:
    history = await h.client.get_workflow_handle(WORKFLOW_ID).fetch_history()
    return any(event.HasField("activity_task_cancel_requested_event_attributes") for event in history.events)


async def _cancel_inside_the_activity(h: Harness, cancelled: list[bool]) -> None:
    """Cancel the run from inside an in-flight scripted activity and hold it until the cancel reaches it.

    The workflow answers a cancel by asking the server to cancel its in-flight activity. A fake
    activity that returns at once can complete in between, and the time-skipping test server then
    rejects the workflow's whole task completion and stalls the run. Holding the activity until the
    history shows the cancel request closes that window; the real server accepts the race.
    """
    cancelled.append(True)
    await h.client.get_workflow_handle(WORKFLOW_ID).cancel()
    await eventually(lambda: _cancel_requested_for_an_activity(h), bool, timeout=REAL_TIMEOUT_SECONDS)


def _cancel_on_the_first_status_poll(h: Harness, cancelled: list[bool]) -> None:
    """Make the first status poll of the first attempt cancel the run from inside that poll."""

    async def cancel(app_name: str, _scheduled: datetime) -> None:
        if app_name == FIRST and not cancelled:
            await _cancel_inside_the_activity(h, cancelled)

    h.fakes.status_hook = cancel


def test_cancelled_run_fences_its_live_attempt_before_it_releases_the_slot():
    """A cancel during an attempt deletes its job and waits, renewing, for its pods to go before the slot is freed."""

    async def scenario(h: Harness) -> None:
        h.fakes.pods_live_for[FIRST] = timedelta(minutes=10)
        cancelled: list[bool] = []

        async def cancel_two_minutes_in(app_name: str, scheduled: datetime) -> None:
            if app_name == FIRST and not cancelled and scheduled - h.submit_times()[0] >= timedelta(minutes=2):
                await _cancel_inside_the_activity(h, cancelled)

        h.fakes.status_hook = cancel_two_minutes_in
        handle = await h.start_maintenance(COMPACTION, EXPIRE)
        with pytest.raises(WorkflowFailureError) as caught:
            await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)
        assert isinstance(caught.value.cause, CancelledError)
        assert cancelled == [True]

        commands = await h.commands()
        names = _names(commands)
        renew = names.index("signal:renew")
        delete = _first_after(commands, "delete_maintenance_job", renew)
        release = _first_after(commands, "signal:release", delete)
        assert "signal:release" not in names[:release]
        assert commands[release][1] - h.fakes.delete_times[FIRST] >= timedelta(minutes=10)
        assert h.fakes.pods_times[-1] - h.fakes.delete_times[FIRST] >= timedelta(minutes=10)
        assert h.recorded() == [(COMPACTION, 1, False, "cancelled")]
        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [(COMPACTION, 1)]
        assert await h.parent_payloads() == [{"run_id": RUN_ID, "record_failures": 0}]
        assert await h.admission_holders() == {}

    _run(scenario)


def test_cancel_during_fencing_keeps_fencing_until_the_pods_are_gone():
    """A cancel that arrives while a timed-out attempt is fenced still waits for its pods before the slot is freed."""

    async def scenario(h: Harness) -> None:
        h.fakes.pods_live_for[FIRST] = timedelta(minutes=30)
        cancelled: list[bool] = []

        async def cancel_while_fencing(app_name: str) -> None:
            if app_name == FIRST and not cancelled:
                await _cancel_inside_the_activity(h, cancelled)

        h.fakes.pods_hook = cancel_while_fencing
        handle = await h.start_maintenance(COMPACTION, attempt_deadline_seconds=FENCE_DEADLINE_SECONDS)
        with pytest.raises(WorkflowFailureError):
            await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert cancelled == [True]
        commands = await h.commands()
        release = _first_after(commands, "signal:release", _names(commands).index("delete_maintenance_job"))
        assert commands[release][1] - h.fakes.delete_times[FIRST] >= timedelta(minutes=30)
        assert await h.admission_holders() == {}

    _run(scenario)


def test_cancelled_fence_polls_slowly_once_past_its_bound():
    """A cancelled attempt whose pods stay polls every 30 s for 15 minutes, then every 5 minutes, still renewing."""

    async def scenario(h: Harness) -> None:
        h.fakes.pods_live_for[FIRST] = timedelta(hours=2)
        cancelled: list[bool] = []
        _cancel_on_the_first_status_poll(h, cancelled)
        handle = await h.start_maintenance(COMPACTION)
        with pytest.raises(WorkflowFailureError):
            await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)
        assert cancelled == [True]

        deleted_at = h.fakes.delete_times[FIRST]
        late = [t for t in h.fakes.pods_times if timedelta(minutes=16) <= t - deleted_at < timedelta(hours=2)]
        assert late
        assert all(b - a >= timedelta(minutes=5) for a, b in itertools.pairwise(late))
        assert len(late) <= 21
        early = [t for t in h.fakes.pods_times if t - deleted_at < timedelta(minutes=14)]
        assert all(b - a < timedelta(minutes=1) for a, b in itertools.pairwise(early))
        commands = await h.commands()
        renews = [at for name, at in commands if name == "signal:renew" and at - deleted_at >= timedelta(minutes=16)]
        assert all(b - a <= timedelta(minutes=10) for a, b in itertools.pairwise(renews))
        assert len(renews) >= 10

    _run(scenario)


def test_renew_is_what_keeps_the_slot_of_an_attempt_past_its_lease():
    """An attempt whose pods outlive its lease keeps its slot only because it renews it."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(EXPIRE, 1): [(1, True, None)]}
        h.fakes.pods_live_for[FIRST] = timedelta(minutes=40)
        holders_late: list[dict] = []

        async def look_late(app_name: str) -> None:
            deleted_at = h.fakes.delete_times.get(FIRST)
            late = deleted_at is not None and h.fakes.pods_times[-1] - deleted_at >= timedelta(minutes=30)
            if app_name == FIRST and late and not holders_late:
                holders_late.append(await h.admission_holders())

        h.fakes.pods_hook = look_late
        handle = await h.start_maintenance(COMPACTION, EXPIRE, attempt_deadline_seconds=FENCE_DEADLINE_SECONDS)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        lease = timedelta(seconds=FENCE_DEADLINE_SECONDS + 15 * 60)
        assert h.fakes.delete_times[FIRST] - h.submit_times()[0] + timedelta(minutes=30) > lease
        assert len(holders_late) == 1
        assert list(holders_late[0]) == [FIRST]

    _run(scenario)


def test_unconfirmed_deletion_fails_the_operation_and_keeps_the_slot():
    """Pods still live 15 minutes after the delete fail the operation, and the slot is held until they are gone."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(EXPIRE, 1): [(1, True, None)]}
        h.fakes.pods_live_for[FIRST] = timedelta(minutes=20)
        handle = await h.start_maintenance(COMPACTION, EXPIRE, attempt_deadline_seconds=FENCE_DEADLINE_SECONDS)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert h.recorded() == [(COMPACTION, 1, False, UNCONFIRMED_ERROR), (EXPIRE, 1, True, None)]
        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [(COMPACTION, 1), (EXPIRE, 1)]
        deleted_at = h.fakes.delete_times[FIRST]
        timed_out_at = h.submit_times()[0] + timedelta(seconds=FENCE_DEADLINE_SECONDS)
        recorded_at = datetime.fromisoformat(h.fakes.records[0]["now"])
        assert timedelta(minutes=15) <= recorded_at - timed_out_at < timedelta(minutes=16)

        commands = await h.commands()
        names = _names(commands)
        delete = names.index("delete_maintenance_job")
        release = _first_after(commands, "signal:release", delete)
        released_at = commands[release][1]
        assert released_at - deleted_at >= timedelta(minutes=20)
        assert names.index("record_maintenance_operation_result") < release
        assert _first_after(commands, "submit_maintenance_operation", delete) > release
        last_live_poll = max(t for t in h.fakes.pods_times if t - deleted_at < timedelta(minutes=20))
        assert last_live_poll - deleted_at >= timedelta(minutes=15)
        slow_gaps = [
            b - a
            for a, b in itertools.pairwise(t for t in h.fakes.pods_times if t - deleted_at >= timedelta(minutes=15))
        ]
        assert slow_gaps
        assert all(g >= timedelta(minutes=5) for g in slow_gaps)

    _run(scenario)


def test_attempt_keeps_its_slot_for_its_own_deadline_under_an_older_lease():
    """An admission workflow started with a shorter lease still lets an attempt hold its slot for its own deadline."""

    async def scenario(h: Harness) -> None:
        handle = await h.start_maintenance(COMPACTION, attempt_deadline_seconds=3600)
        await eventually(lambda: _value(len(h.fakes.submits)), lambda n: n == 1)
        await h.env.sleep(timedelta(minutes=20))
        assert list(await h.admission_holders()) == [FIRST]

        await handle.signal(
            TableMaintenanceSignal.OPERATION_RESULT,
            OperationResultSignal(RUN_ID, COMPACTION, 1, True, {"files": 1}, None),
        )
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)
        assert h.recorded() == [(COMPACTION, 1, True, None)]

    _run(scenario, lease_seconds=600)


def test_job_completing_during_fencing_still_counts_as_timed_out():
    """A result that arrives after the deadline, while the attempt is being fenced, does not turn it into a success."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}
        h.fakes.states[FIRST] = {"state": "COMPLETED", "error": None}
        h.fakes.pods_live_polls[FIRST] = 1
        sent: list[str] = []

        async def late_result(app_name: str) -> None:
            if app_name != FIRST or sent:
                return
            sent.append(app_name)
            await h.client.get_workflow_handle(WORKFLOW_ID).signal(
                TableMaintenanceSignal.OPERATION_RESULT,
                OperationResultSignal(RUN_ID, COMPACTION, 1, True, {"files": 7}, None),
            )

        h.fakes.pods_hook = late_result
        handle = await h.start_maintenance(COMPACTION, attempt_deadline_seconds=100)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert sent == [FIRST]
        assert h.recorded() == [(COMPACTION, 1, False, "spark job timed out"), (COMPACTION, 2, True, None)]

    _run(scenario)


FIXTURES = Path(__file__).parent / "fixtures"


def test_history_from_before_fencing_replays():
    """A run that timed out under the code before fencing replays on the new code without non-determinism."""

    async def go() -> None:
        history = WorkflowHistory.from_json(
            WORKFLOW_ID, (FIXTURES / "maintenance_timeout_before_fencing.json").read_text()
        )
        await Replayer(workflows=[TableMaintenanceWorkflow]).replay_workflow(history)

    asyncio.run(go())


def test_history_from_before_failure_classes_replays():
    """A run whose attempts all failed under the code before failure classes replays without non-determinism."""

    async def go() -> None:
        history = WorkflowHistory.from_json(
            WORKFLOW_ID, (FIXTURES / "maintenance_failures_before_failure_classes.json").read_text()
        )
        await Replayer(workflows=[TableMaintenanceWorkflow]).replay_workflow(history)

    asyncio.run(go())


OOM_ERROR = "java.lang.OutOfMemoryError: Java heap space"


def _sizes(h: Harness, operation: str = COMPACTION) -> list[str]:
    return [s["size"] for s in h.fakes.submits if s["operation"] == operation]


def test_first_attempt_uses_the_plan_start_size():
    """The first attempt of an operation runs at the size its plan starts it at."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 1): [(1, True, None)]}
        await h.run_maintenance(COMPACTION, start_size="M")
        assert _sizes(h) == ["M"]

    _run(scenario)


def test_plan_without_start_size_submits_size_s():
    """A plan from before sizes existed starts its operations at S."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 1): [(1, True, None)]}
        await h.run_maintenance(COMPACTION)
        assert _sizes(h) == ["S"]

    _run(scenario)


def test_attempts_follow_the_recorded_size_decision():
    """Each retry runs at the size the record of the failed attempt decided."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {
            (COMPACTION, 1): [(1, False, OOM_ERROR)],
            (COMPACTION, 2): [(2, False, OOM_ERROR)],
            (COMPACTION, 3): [(3, True, None)],
        }
        h.fakes.record_replies = {
            (COMPACTION, 1): {"failure_class": "oom", "next_step": "retry_larger", "next_size": "M"},
            (COMPACTION, 2): {"failure_class": "oom", "next_step": "retry_larger", "next_size": "L"},
        }
        await h.run_maintenance(COMPACTION)
        assert _sizes(h) == ["S", "M", "L"]

    _run(scenario)


def test_needs_attention_stops_the_operation_without_another_attempt():
    """An attempt that needs a person ends its operation at once, and the next operation still runs."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {
            (COMPACTION, 1): [(1, False, OOM_ERROR)],
            (COMPACTION, 2): [(2, False, OOM_ERROR)],
            (EXPIRE, 1): [(1, True, None)],
        }
        h.fakes.record_replies = {
            (COMPACTION, 1): {"failure_class": "oom", "next_step": "retry_larger", "next_size": "L"},
            (COMPACTION, 2): {"failure_class": "oom", "next_step": "needs_attention", "next_size": None},
        }
        await h.run_maintenance(COMPACTION, EXPIRE, start_size="M")

        assert _sizes(h) == ["M", "L"]
        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [
            (COMPACTION, 1),
            (COMPACTION, 2),
            (EXPIRE, 1),
        ]
        times = h.submit_times()
        assert times[2] - times[1] < timedelta(seconds=60)
        assert await h.parent_payloads() == [{"run_id": RUN_ID, "record_failures": 0}]

    _run(scenario)


def test_record_result_without_a_decision_keeps_retrying_at_the_same_size():
    """A record reply without a next step, as before failure classes, retries three times at the same size."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {
            (COMPACTION, 1): [(1, False, OOM_ERROR)],
            (COMPACTION, 2): [(2, False, OOM_ERROR)],
            (COMPACTION, 3): [(3, False, OOM_ERROR)],
        }
        await h.run_maintenance(COMPACTION)
        assert _sizes(h) == ["S", "S", "S"]

    _run(scenario)


def test_failed_record_keeps_retrying_at_the_same_size():
    """A record that could not be stored has no decision, so the next attempt runs at the same size."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 1): [(1, False, OOM_ERROR)], (COMPACTION, 2): [(2, True, None)]}
        h.fakes.record_errors = {(COMPACTION, 1)}
        await h.run_maintenance(COMPACTION, start_size="M")
        assert _sizes(h) == ["M", "M"]

    _run(scenario)


def _ending_by_callback(h: Harness) -> None:
    h.fakes.callbacks = {(COMPACTION, 1): [(1, False, "boom")], (COMPACTION, 2): [(2, True, None)]}


def _ending_by_failed_state(h: Harness) -> None:
    h.fakes.states[FIRST] = {"state": "FAILED", "error": "driver died"}
    h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}


def _ending_by_missing_job(h: Harness) -> None:
    h.fakes.states[FIRST] = {"state": "NOT_FOUND", "error": None}
    h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}


def _ending_by_submit_error(h: Harness) -> None:
    h.fakes.submit_errors = {(COMPACTION, 1): "attempt already started"}
    h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}


def _ending_by_timeout(h: Harness) -> None:
    h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}


@pytest.mark.parametrize(
    ("script", "deadline", "ending"),
    [
        (_ending_by_callback, ATTEMPT_DEADLINE_SECONDS, "result"),
        (_ending_by_failed_state, ATTEMPT_DEADLINE_SECONDS, "job_failed"),
        (_ending_by_timeout, FENCE_DEADLINE_SECONDS, "timed_out"),
        (_ending_by_missing_job, ATTEMPT_DEADLINE_SECONDS, "missing"),
        (_ending_by_submit_error, ATTEMPT_DEADLINE_SECONDS, "submit_failed"),
    ],
)
def test_record_reaches_the_ending_of_each_failure(script, deadline, ending):
    """Each failed attempt is recorded with how it ended, every record with the attempt limit."""

    async def scenario(h: Harness) -> None:
        script(h)
        handle = await h.start_maintenance(COMPACTION, attempt_deadline_seconds=deadline)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert [(r["attempt"], r["succeeded"], r["ended_by"]) for r in h.fakes.records] == [
            (1, False, ending),
            (2, True, "result"),
        ]
        assert all(r["max_attempts"] == 3 and r["still_running"] is False for r in h.fakes.records)

    _run(scenario)


def test_records_carry_the_policy_the_run_was_planned_under():
    """Every record names the policy of the plan, so a needs-attention mark is set under it."""

    async def scenario(h: Harness) -> None:
        _ending_by_failed_state(h)
        await h.run_maintenance(COMPACTION)

        assert [(r["policy_name"], r["policy_version"], r["policy_target"]) for r in h.fakes.records] == [
            PLANNED_POLICY,
            PLANNED_POLICY,
        ]

    _run(scenario)


def test_cancelled_attempt_is_recorded_as_cancelled():
    """An attempt interrupted by a cancel is recorded as ended by the cancel."""

    async def scenario(h: Harness) -> None:
        cancelled: list[bool] = []
        _cancel_on_the_first_status_poll(h, cancelled)
        handle = await h.start_maintenance(COMPACTION)
        with pytest.raises(WorkflowFailureError):
            await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert cancelled == [True]
        assert [(r["attempt"], r["ended_by"], r["max_attempts"]) for r in h.fakes.records] == [(1, "cancelled", 3)]

    _run(scenario)


def test_unconfirmed_fence_records_still_running():
    """An attempt whose pods outlived the confirm bound is recorded as possibly still running."""

    async def scenario(h: Harness) -> None:
        h.fakes.pods_live_for[FIRST] = timedelta(minutes=20)
        handle = await h.start_maintenance(COMPACTION, attempt_deadline_seconds=FENCE_DEADLINE_SECONDS)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert [(r["attempt"], r["ended_by"], r["still_running"]) for r in h.fakes.records] == [(1, "timed_out", True)]

    _run(scenario)


def test_failed_attempt_is_recorded_before_its_job_is_deleted():
    """A failure Spark reported is recorded while its job and pods still exist, so their evidence can be read."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 1): [(1, False, OOM_ERROR)], (COMPACTION, 2): [(2, True, None)]}
        await h.run_maintenance(COMPACTION)

        names = _names(await h.commands())
        assert names.index("record_maintenance_operation_result") < names.index("delete_maintenance_job")

    _run(scenario)


def test_failed_admission_is_recorded_as_admission_failed():
    """An attempt whose admission request could not be sent is recorded as ended by the failed admission."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}
        await h.run_maintenance(COMPACTION)

        assert [(r["attempt"], r["succeeded"], r["ended_by"]) for r in h.fakes.records] == [
            (1, False, "admission_failed"),
            (2, True, "result"),
        ]
        assert h.fakes.records[0]["error"] == "admission acquire failed: admission workflow unavailable"
        assert [s["attempt"] for s in h.fakes.submits] == [2]

    _run(scenario, failing_acquires=frozenset({f"{RUN_ID}-{COMPACTION}-1"}))


ALL_PARTITIONS = [{"spec_id": 0, "where": "region IN ('eu', 'us', 'ap', 'sa')"}]
TOP_HALF = [{"spec_id": 0, "where": "region IN ('eu', 'us')"}]
TOP_QUARTER = [{"spec_id": 0, "where": "region IN ('eu')"}]


def _narrowable_plan(*filter_sets: list[dict]) -> dict:
    plan = _plan(COMPACTION)
    plan["operations"][0] = {**plan["operations"][0], "filters": filter_sets[0], "filter_sets": list(filter_sets)}
    return plan


def _filters(h: Harness) -> list[list[dict]]:
    return [s["filters"] for s in h.fakes.submits if s["operation"] == COMPACTION]


def _failing(h: Harness, failure_class: str, step: str, attempts: int = 2) -> None:
    h.fakes.callbacks = {(COMPACTION, a): [(a, False, OOM_ERROR)] for a in range(1, attempts + 1)}
    h.fakes.callbacks[(COMPACTION, attempts + 1)] = [(attempts + 1, True, None)]
    h.fakes.record_replies = {
        (COMPACTION, a): {"failure_class": failure_class, "next_step": step, "next_size": "M"}
        for a in range(1, attempts + 1)
    }


def test_oom_retry_submits_the_top_half_of_the_partitions():
    """Each out-of-memory retry submits fewer partitions: all of them, the best half, the best quarter."""

    async def scenario(h: Harness) -> None:
        _failing(h, "oom", "retry_larger")
        await h.run_maintenance(plan=_narrowable_plan(ALL_PARTITIONS, TOP_HALF, TOP_QUARTER))
        assert _filters(h) == [ALL_PARTITIONS, TOP_HALF, TOP_QUARTER]

    _run(scenario)


def test_oom_retry_past_the_smallest_set_keeps_it():
    """Once the smallest set was tried, further out-of-memory retries keep it."""

    async def scenario(h: Harness) -> None:
        _failing(h, "oom", "retry_larger")
        await h.run_maintenance(plan=_narrowable_plan(ALL_PARTITIONS, TOP_HALF))
        assert _filters(h) == [ALL_PARTITIONS, TOP_HALF, TOP_HALF]

    _run(scenario)


def test_other_failures_retry_the_same_partitions():
    """A retry after a failure that is not out of memory submits the same partitions."""

    async def scenario(h: Harness) -> None:
        _failing(h, "other", "retry_same")
        await h.run_maintenance(plan=_narrowable_plan(ALL_PARTITIONS, TOP_HALF, TOP_QUARTER))
        assert _filters(h) == [ALL_PARTITIONS, ALL_PARTITIONS, ALL_PARTITIONS]

    _run(scenario)


def test_plan_without_filter_sets_retries_its_filters():
    """A plan from before filter sets submits its filters on every attempt."""

    async def scenario(h: Harness) -> None:
        _failing(h, "oom", "retry_larger")
        await h.run_maintenance(COMPACTION)
        assert _filters(h) == [[{"spec_id": 0, "where": f"{COMPACTION} = 1"}]] * 3

    _run(scenario)


def test_history_from_before_fewer_partitions_replays():
    """A run retried after running out of memory under the code before, with a plan carrying filter sets, replays."""

    async def go() -> None:
        history = WorkflowHistory.from_json(
            WORKFLOW_ID, (FIXTURES / "maintenance_oom_before_fewer_partitions.json").read_text()
        )
        await Replayer(workflows=[TableMaintenanceWorkflow]).replay_workflow(history)

    asyncio.run(go())
