"""Test the TableMaintenanceWorkflow on a time-skipping Temporal test server."""

from __future__ import annotations

import asyncio
import contextlib
import itertools
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from temporalio.client import WorkflowFailureError
from temporalio.exceptions import ApplicationError, CancelledError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer, UnsandboxedWorkflowRunner, Worker

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    TABLE_MAINTENANCE_WORKFLOW,
    OperationResultSignal,
    RaisePrioritySignal,
    TableMaintenanceSignal,
    TableMaintenanceWorkflowInput,
    table_maintenance_workflow_id,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import (
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
from tests.context.table_maintenance.numbered_id import numbered_id

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from temporalio.client import Client, WorkflowHandle

COMPACTION = "rewrite_data_files"
EXPIRE = "expire_snapshots"
ORPHANS = "remove_orphan_files"
RUN_IDS = (numbered_id("mr", 1), numbered_id("mr", 2), numbered_id("mr", 3), numbered_id("mr", 4))
PREVIOUS_RUN_ID = "mr-00000000000000000000000000"
TABLE = "iceberg.e2e.t"
TABLE_UUID = "u1"
WORKFLOW_ID = table_maintenance_workflow_id(TABLE_UUID)
PARENT_ID = "parent-1"
REAL_TIMEOUT_SECONDS = 60
ATTEMPT_DEADLINE_SECONDS = 21600
QUEUE_WAIT_LIMIT_SECONDS = 86400
PLANNED_POLICY = ("mp-00000000000000000000000004", 2, {"type": "namespace", "path": ["iceberg", "sales"]})
PLANNED_POLICY_NAME = "nightly"
# Once a run ended, each of its attempts' jobs is checked once more (status, pods) until it is gone.
AFTER_RUN_CHECK = 1


def _plan(*operations: str, start_size: str = "S") -> dict:
    return {
        "status": "planned",
        "reason": None,
        "schedule_interval_seconds": 3600,
        "catalog_commit_debounce_seconds": 300,
        "table_name": TABLE,
        "policy_id": PLANNED_POLICY[0],
        "policy_name": PLANNED_POLICY_NAME,
        "policy_version": PLANNED_POLICY[1],
        "policy_target": PLANNED_POLICY[2],
        "operations": [
            {
                "operation": op,
                "content": {"operation": op},
                "start_size": start_size,
            }
            for op in operations
        ],
    }


def _report(
    *,
    run_ids: list[str] | None = None,
    record_failures: int = 0,
    unapplied_raise: bool = False,
    raises_received: int = 0,
) -> dict:
    """Return the report the workflow sends its parent when it finishes, for its runs (the first one by default)."""
    return {
        "run_ids": run_ids if run_ids is not None else [RUN_IDS[0]],
        "record_failures": record_failures,
        "unapplied_raise": unapplied_raise,
        "raises_received": raises_received,
    }


@dataclass
class Harness:
    """Run the maintenance workflow against scripted activities and a parent stub."""

    env: WorkflowEnvironment
    client: Client
    queue: str
    fakes: ScriptedMaintenanceActivities
    raise_sent_at: datetime | None = None

    async def run_maintenance(
        self,
        *operations: str,
        parent_id: str = PARENT_ID,
        start_size: str = "S",
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
        queue_wait_limit_seconds: int = QUEUE_WAIT_LIMIT_SECONDS,
        start_size: str = "S",
        plan: dict | None = None,
        raise_at_start: RaisePrioritySignal | None = None,
    ) -> WorkflowHandle:
        """Start the maintenance workflow for the operations, or for ``plan``, and return its handle.

        ``raise_at_start``, when set, is sent with the start, so the workflow holds it before its first command.
        """
        signal: dict = {}
        if raise_at_start is not None:
            signal = {"start_signal": TableMaintenanceSignal.RAISE_PRIORITY, "start_signal_args": [raise_at_start]}
        return await self.client.start_workflow(
            TABLE_MAINTENANCE_WORKFLOW,
            TableMaintenanceWorkflowInput(
                run_ids=list(RUN_IDS[: len((plan or _plan(*operations))["operations"])]),
                table_uuid=TABLE_UUID,
                parent_workflow_id=parent_id,
                trigger="scheduled",
                plan=plan or _plan(*operations, start_size=start_size),
                attempt_deadline_seconds=attempt_deadline_seconds,
                max_attempts=max_attempts,
                queue_wait_limit_seconds=queue_wait_limit_seconds,
            ),
            id=WORKFLOW_ID,
            task_queue=self.queue,
            **signal,
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


def _run(scenario: Callable[[Harness], Awaitable[None]], *, max_cached_workflows: int = 1000) -> None:
    """Run ``scenario`` against the workflow on a time-skipping server, with the real parent signal activity.

    ``max_cached_workflows=0`` makes the worker replay the history on every workflow task.
    """

    async def go() -> None:
        async with await WorkflowEnvironment.start_time_skipping() as env:
            queue = TASK_QUEUE
            fakes = ScriptedMaintenanceActivities(env.client)
            signals = table_maintenance_activities_with_fakes(client=env.client)
            async with (
                Worker(
                    env.client,
                    task_queue=queue,
                    workflows=[TableMaintenanceWorkflow],
                    activities=[*fakes.all(), signals.signal_parent],
                    max_cached_workflows=max_cached_workflows,
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

        assert [s["run_id"] for s in h.fakes.submits] == list(RUN_IDS[:2])
        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [
            (COMPACTION, 1),
            (EXPIRE, 1),
        ]
        assert h.recorded() == [(COMPACTION, 1, True, None), (EXPIRE, 1, True, None)]
        assert h.fakes.records[0]["metrics"] == {"files": 1}
        assert h.fakes.deletes == [
            f"{RUN_IDS[0]}-{COMPACTION}-1",
            f"{RUN_IDS[1]}-{EXPIRE}-1",
        ]
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:2]))]

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
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:2]))]

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
        h.fakes.states[f"{RUN_IDS[0]}-{COMPACTION}-2"] = {"state": "FAILED", "error": None}
        await h.run_maintenance(COMPACTION)

        assert h.recorded() == [
            (COMPACTION, 1, False, "boom-1"),
            (COMPACTION, 2, False, "spark job failed"),
            (COMPACTION, 3, True, None),
        ]
        attempts = [f"{RUN_IDS[0]}-{COMPACTION}-{attempt}" for attempt in (1, 2, 3)]
        # Attempt 2's one poll, then the check after the run that each attempt's job is gone.
        assert h.fakes.status_calls == [attempts[1], *attempts]

    _run(scenario)


def test_polling_detects_crashed_driver():
    """Polling a job whose driver crashed records the attempt as failed."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 3): [(3, True, None)]}
        h.fakes.states[f"{RUN_IDS[0]}-{COMPACTION}-1"] = {"state": "FAILED", "error": None}
        h.fakes.states[f"{RUN_IDS[0]}-{COMPACTION}-2"] = {"state": "FAILED", "error": "oom"}
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
        h.fakes.states[f"{RUN_IDS[0]}-{COMPACTION}-1"] = {
            "state": "NOT_FOUND",
            "error": None,
        }
        h.fakes.states[f"{RUN_IDS[0]}-{COMPACTION}-2"] = {
            "state": "COMPLETED",
            "error": None,
        }
        await h.run_maintenance(COMPACTION)

        assert h.recorded() == [
            (COMPACTION, 1, False, "spark job missing"),
            (COMPACTION, 2, True, None),
        ]
        assert h.fakes.records[1]["metrics"] == {"completed_without_callback": 1}
        completed_polls = h.fakes.status_calls.count(f"{RUN_IDS[0]}-{COMPACTION}-2")
        assert completed_polls == 5 + AFTER_RUN_CHECK

    _run(scenario)


def test_job_deleted_when_submit_activity_fails():
    """A failed submit is recorded, its job deleted, and the next attempt follows after the first backoff."""

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
            f"{RUN_IDS[0]}-{COMPACTION}-1",
            f"{RUN_IDS[0]}-{COMPACTION}-2",
        ]

    _run(scenario)


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
        h.fakes.states[f"{RUN_IDS[0]}-{COMPACTION}-1"] = [completed, running, completed]
        await h.run_maintenance(COMPACTION)

        assert h.recorded() == [(COMPACTION, 1, True, None)]
        assert h.fakes.status_calls.count(f"{RUN_IDS[0]}-{COMPACTION}-1") == 7 + AFTER_RUN_CHECK

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
            f"{RUN_IDS[0]}-{COMPACTION}-1",
            f"{RUN_IDS[0]}-{COMPACTION}-1",
            f"{RUN_IDS[0]}-{COMPACTION}-2",
        ]

    _run(scenario)


def test_poll_interval_backs_off_after_ten_minutes():
    """Status polls are under a minute apart for the first ten minutes and at least five minutes apart later."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}
        await h.run_maintenance(COMPACTION)

        app = f"{RUN_IDS[0]}-{COMPACTION}-1"
        submitted = h.submit_times()[0]
        polls = [t for t, name in zip(h.fakes.status_times, h.fakes.status_calls, strict=True) if name == app]
        first_hour = [t for t in polls if t - submitted < timedelta(hours=1, seconds=30)]
        assert len(first_hour) == 20 + 10
        gaps = [b - a for a, b in zip(polls, polls[1:], strict=False)]
        assert all(g < timedelta(seconds=60) for g in gaps[:19])
        assert all(g >= timedelta(minutes=5) for g in gaps[20:])
        assert len(polls) < 100

    _run(scenario)


def test_cancelled_workflow_records_deletes_and_notifies():
    """A cancelled workflow records the cancellation, deletes the job and notifies the parent."""

    async def scenario(h: Harness) -> None:
        cancelled: list[bool] = []
        _cancel_on_the_first_status_poll(h, cancelled)
        handle = await h.start_maintenance(COMPACTION, EXPIRE)
        with pytest.raises(WorkflowFailureError) as caught:
            await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)
        assert isinstance(caught.value.cause, CancelledError)
        assert cancelled == [True]

        assert h.recorded() == [(COMPACTION, 1, False, "cancelled")]
        assert set(h.fakes.deletes) == {f"{RUN_IDS[0]}-{COMPACTION}-1"}
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:2]))]

    _run(scenario)


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
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:2]), record_failures=1)]

    _run(scenario)


async def _value(value: object) -> object:
    return value


async def _cancel_while_blocked(
    h: Harness,
    gate: asyncio.Event,
    blocked: Callable[[], bool],
    advance: timedelta = timedelta(0),
    operations: tuple[str, ...] = (COMPACTION, EXPIRE),
) -> None:
    handle = await h.start_maintenance(*operations)
    try:
        await eventually(lambda: _value(len(h.fakes.submits)), lambda n: n == 1)
        if advance:
            await h.env.sleep(advance)
        await eventually(lambda: _value(blocked()), bool)
        await handle.cancel()
        # The blocked activity is let go once the cancel reached it: the jobs are then waited for until gone.
        await eventually(lambda: _cancel_requested_for_an_activity(h), bool, timeout=REAL_TIMEOUT_SECONDS)
        gate.set()
        with pytest.raises(WorkflowFailureError) as caught:
            await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)
    finally:
        gate.set()
    assert isinstance(caught.value.cause, CancelledError)
    assert h.recorded() == [(COMPACTION, 1, False, "cancelled")]
    assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [(COMPACTION, 1)]
    assert set(h.fakes.deletes) == {f"{RUN_IDS[0]}-{COMPACTION}-1"}
    assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[: len(operations)]))]


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
        assert h.fakes.status_calls == [f"{RUN_IDS[0]}-{COMPACTION}-1"] * (1 + AFTER_RUN_CHECK)
        assert [s["run_id"] for s in h.fakes.skips] == [RUN_IDS[1]]

    _run(scenario)


def test_cancel_during_submit_activity_cancels_the_workflow():
    """A cancel while the submit activity is running cancels the workflow."""

    async def scenario(h: Harness) -> None:
        gate = h.fakes.submit_gate = asyncio.Event()
        await _cancel_while_blocked(h, gate, lambda: len(h.fakes.submits) == 1)
        assert [s["run_id"] for s in h.fakes.skips] == [RUN_IDS[0], RUN_IDS[1]]

    _run(scenario)


def test_result_arriving_during_last_poll_before_deadline_wins():
    """A result that arrives during the last poll before the deadline counts as the outcome of the attempt."""

    async def scenario(h: Harness) -> None:
        deadline = timedelta(seconds=100)
        app = f"{RUN_IDS[0]}-{COMPACTION}-1"
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
                OperationResultSignal(RUN_IDS[0], COMPACTION, 1, True, {"files": 7}, None),
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
FIRST = f"{RUN_IDS[0]}-{COMPACTION}-1"


def _names(commands: list[tuple[str, datetime]]) -> list[str]:
    return [name for name, _ in commands]


def _first_after(commands: list[tuple[str, datetime]], name: str, start: int) -> int:
    return next(i for i in range(start, len(commands)) if commands[i][0] == name)


def test_timed_out_attempt_deletes_the_job_before_the_next_attempt():
    """A timed-out attempt deletes its job and confirms its pods are gone before the next attempt is submitted."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}
        handle = await h.start_maintenance(COMPACTION, attempt_deadline_seconds=FENCE_DEADLINE_SECONDS)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        commands = await h.commands()
        names = _names(commands)
        delete = names.index("delete_maintenance_job")
        pods = _first_after(commands, "get_maintenance_job_processes", delete)
        second_submit = _first_after(commands, "submit_maintenance_operation", pods)
        assert names.index("submit_maintenance_operation") < delete < pods < second_submit
        assert h.recorded() == [(COMPACTION, 1, False, "spark job timed out"), (COMPACTION, 2, True, None)]
        # The fence's one poll, then the check after the run that each attempt's job is gone.
        assert h.fakes.pods_calls == [FIRST, FIRST, f"{RUN_IDS[0]}-{COMPACTION}-2"]

    _run(scenario)


def test_next_attempt_is_not_submitted_while_pods_are_live():
    """The next attempt is submitted only after a poll finds the timed-out attempt's pods gone."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}
        h.fakes.pods_live_polls[FIRST] = 3
        handle = await h.start_maintenance(COMPACTION, attempt_deadline_seconds=FENCE_DEADLINE_SECONDS)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert h.fakes.pods_calls == [*[FIRST] * 4, FIRST, f"{RUN_IDS[0]}-{COMPACTION}-2"]
        fence_polls = h.fakes.pods_times[:4]
        gaps = [b - a for a, b in itertools.pairwise(fence_polls)]
        assert all(timedelta(seconds=30) <= g < timedelta(seconds=60) for g in gaps)
        assert h.submit_times()[1] > fence_polls[-1]
        assert h.recorded() == [(COMPACTION, 1, False, "spark job timed out"), (COMPACTION, 2, True, None)]

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


def test_job_that_cannot_be_deleted_fails_the_operation_and_waits_for_the_delete():
    """A job still not deleted 15 minutes after the timeout fails the operation; the next one waits for the delete."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(EXPIRE, 1): [(1, True, None)]}
        h.fakes.delete_failures[FIRST] = 40
        handle = await h.start_maintenance(COMPACTION, EXPIRE, attempt_deadline_seconds=FENCE_DEADLINE_SECONDS)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        undeletable = "spark job timed out; its job could still not be deleted 15 minutes after the timeout"
        assert h.recorded() == [(COMPACTION, 1, False, undeletable), (EXPIRE, 1, True, None)]
        assert h.fakes.pods_times[0] >= h.fakes.delete_times[FIRST]
        assert h.submit_times()[1] >= h.fakes.delete_times[FIRST]

    _run(scenario)


def test_missing_job_is_fenced_before_the_next_attempt():
    """A job that went missing is deleted and its pods waited for before the next attempt is submitted."""

    async def scenario(h: Harness) -> None:
        h.fakes.states[FIRST] = {"state": "NOT_FOUND", "error": None}
        h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}
        h.fakes.pods_live_polls[FIRST] = 3
        await h.run_maintenance(COMPACTION)

        commands = await h.commands()
        names = _names(commands)
        second_submit = _first_after(
            commands, "submit_maintenance_operation", names.index("submit_maintenance_operation") + 1
        )
        assert names.index("delete_maintenance_job") < second_submit
        assert h.fakes.pods_calls == [*[FIRST] * 4, FIRST, f"{RUN_IDS[0]}-{COMPACTION}-2"]
        assert h.submit_times()[1] > h.fakes.pods_times[3]
        assert h.recorded() == [(COMPACTION, 1, False, "spark job missing"), (COMPACTION, 2, True, None)]

    _run(scenario)


def test_missing_job_whose_pods_stay_fails_the_operation_and_waits_for_them():
    """Pods of a missing job still live 15 minutes later fail the operation; the next one waits for them."""

    async def scenario(h: Harness) -> None:
        h.fakes.states[FIRST] = {"state": "NOT_FOUND", "error": None}
        h.fakes.callbacks = {(EXPIRE, 1): [(1, True, None)]}
        h.fakes.pods_live_for[FIRST] = timedelta(minutes=20)
        await h.run_maintenance(COMPACTION, EXPIRE)

        stuck = "spark job missing; its pods were still running 15 minutes after the job went missing"
        assert h.recorded() == [(COMPACTION, 1, False, stuck), (EXPIRE, 1, True, None)]
        assert h.submit_times()[1] - h.fakes.delete_times[FIRST] >= timedelta(minutes=20)

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


def test_cancelled_run_fences_its_live_attempt_before_it_reports():
    """A cancel during an attempt deletes its job and waits for its pods to go before the parent is told."""

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
        delete = names.index("delete_maintenance_job")
        report = _first_after(commands, "signal_parent", delete)
        assert commands[report][1] - h.fakes.delete_times[FIRST] >= timedelta(minutes=10)
        assert h.fakes.pods_times[-1] - h.fakes.delete_times[FIRST] >= timedelta(minutes=10)
        assert h.recorded() == [(COMPACTION, 1, False, "cancelled")]
        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [(COMPACTION, 1)]
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:2]))]

    _run(scenario)


def test_cancel_during_fencing_keeps_fencing_until_the_pods_are_gone():
    """A cancel that arrives while a timed-out attempt is fenced still waits for its pods before the parent is told."""

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
        report = _first_after(commands, "signal_parent", _names(commands).index("delete_maintenance_job"))
        assert commands[report][1] - h.fakes.delete_times[FIRST] >= timedelta(minutes=30)

    _run(scenario)


def test_cancelled_fence_polls_slowly_once_past_its_bound():
    """A cancelled attempt whose pods stay polls every 30 s for 15 minutes, then every 5 minutes."""

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

    _run(scenario)


def test_unconfirmed_deletion_fails_the_operation_and_waits_for_the_pods():
    """Pods still live 15 minutes after the delete fail the operation; the next one waits until they are gone."""

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
        next_submit = _first_after(commands, "submit_maintenance_operation", names.index("delete_maintenance_job"))
        assert commands[next_submit][1] - deleted_at >= timedelta(minutes=20)
        assert names.index("record_maintenance_operation_result") < next_submit
        fence_polls = h.fakes.pods_times[:-2]  # the last two check, after each run, that its job is gone
        last_live_poll = max(t for t in fence_polls if t - deleted_at < timedelta(minutes=20))
        assert last_live_poll - deleted_at >= timedelta(minutes=15)
        slow_gaps = [
            b - a for a, b in itertools.pairwise(t for t in fence_polls if t - deleted_at >= timedelta(minutes=15))
        ]
        assert slow_gaps
        assert all(g >= timedelta(minutes=5) for g in slow_gaps)

    _run(scenario)


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
                OperationResultSignal(RUN_IDS[0], COMPACTION, 1, True, {"files": 7}, None),
            )

        h.fakes.pods_hook = late_result
        handle = await h.start_maintenance(COMPACTION, attempt_deadline_seconds=100)
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert sent == [FIRST]
        assert h.recorded() == [(COMPACTION, 1, False, "spark job timed out"), (COMPACTION, 2, True, None)]

    _run(scenario)


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
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:2]))]

    _run(scenario)


def test_record_result_without_a_decision_keeps_retrying_at_the_same_size():
    """A record reply that names no next step retries three times at the same size."""

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
    """Every record names the policy of the plan and its name then, so a needs-attention mark is set under it."""

    async def scenario(h: Harness) -> None:
        _ending_by_failed_state(h)
        await h.run_maintenance(COMPACTION)

        assert [(r["policy_id"], r["policy_version"], r["policy_target"]) for r in h.fakes.records] == [
            PLANNED_POLICY,
            PLANNED_POLICY,
        ]
        assert [r["policy_name"] for r in h.fakes.records] == [PLANNED_POLICY_NAME, PLANNED_POLICY_NAME]

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


PLANNED_CONTENT = {"operation": COMPACTION, "target_file_size_bytes": 1024, "options": {}, "partitions": []}


def test_oom_retry_keeps_the_planned_content():
    """No attempt, also after running out of memory, sends job content of its own: the submit reads the run's."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, a): [(a, False, OOM_ERROR)] for a in (1, 2)}
        h.fakes.callbacks[(COMPACTION, 3)] = [(3, True, None)]
        h.fakes.record_replies = {
            (COMPACTION, a): {"failure_class": "oom", "next_step": "retry_larger", "next_size": "M"} for a in (1, 2)
        }
        plan = _plan(COMPACTION)
        plan["operations"][0] = {
            **plan["operations"][0],
            "content": PLANNED_CONTENT,
        }
        await h.run_maintenance(plan=plan)
        assert len(h.fakes.submits) == 3
        assert not [s for s in h.fakes.submits if "content" in s]

    _run(scenario)


def test_the_first_command_is_the_first_submit():
    """The workflow creates no run: its first command is the first submit, and nothing is signalled before it."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 1): [(1, True, None)]}
        await h.run_maintenance(COMPACTION)

        names = _names(await h.commands())
        assert names[0] == "submit_maintenance_operation"
        assert not [name for name in names if name.startswith("signal:")]

    _run(scenario)


def test_late_result_of_another_run_is_ignored():
    """A result of an earlier run of the table, sent to the table's workflow id, is ignored; the own result counts."""

    async def scenario(h: Harness) -> None:
        handle = await h.start_maintenance(COMPACTION)
        await eventually(lambda: _value(len(h.fakes.submits)), lambda n: n == 1)
        await handle.signal(
            TableMaintenanceSignal.OPERATION_RESULT,
            OperationResultSignal(PREVIOUS_RUN_ID, COMPACTION, 1, False, {}, "late failure"),
        )
        await handle.signal(
            TableMaintenanceSignal.OPERATION_RESULT,
            OperationResultSignal(RUN_IDS[0], COMPACTION, 1, True, {"files": 3}, None),
        )
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert h.recorded() == [(COMPACTION, 1, True, None)]
        assert all(r["run_id"] == RUN_IDS[0] for r in h.fakes.records)
        assert h.fakes.records[0]["metrics"] == {"files": 3}

    _run(scenario)


QUEUED_FOR = timedelta(hours=3)
SHORT_DEADLINE = timedelta(hours=1)
FIRST_APP = f"{RUN_IDS[0]}-{COMPACTION}-1"


async def _run_with_a_short_deadline(h: Harness) -> None:
    """Run one compaction whose first attempt has a one-hour deadline and whose second attempt succeeds."""
    h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}
    handle = await h.start_maintenance(COMPACTION, attempt_deadline_seconds=int(SHORT_DEADLINE.total_seconds()))
    await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)


def test_queue_wait_does_not_count_toward_the_deadline():
    """An attempt queued for three hours is not timed out at its one-hour deadline; it is one hour after its start."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = (QUEUED_FOR, QUEUED_FOR)
        await _run_with_a_short_deadline(h)

        assert h.recorded() == [(COMPACTION, 1, False, "spark job timed out"), (COMPACTION, 2, True, None)]
        assert h.fakes.records[0]["ended_by"] == "timed_out"
        first, second = h.submit_times()
        assert QUEUED_FOR + SHORT_DEADLINE <= second - first < QUEUED_FOR + SHORT_DEADLINE + timedelta(minutes=3)

    _run(scenario)


def test_attempt_is_recorded_running_once():
    """The first poll that sees the driver started records the attempt running, with the driver's start."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = (QUEUED_FOR, QUEUED_FOR)
        await _run_with_a_short_deadline(h)

        first = h.submit_times()[0]
        records = [r for r in h.fakes.running_records if r["attempt"] == 1]
        assert len(records) == 1
        assert (records[0]["run_id"], records[0]["operation"]) == (RUN_IDS[0], COMPACTION)
        assert datetime.fromisoformat(records[0]["started_running_at"]) == first + QUEUED_FOR
        assert datetime.fromisoformat(records[0]["now"]) >= first + QUEUED_FOR

    _run(scenario)


def test_queued_past_the_limit_ends_queue_timed_out():
    """An attempt whose driver never starts is fenced at the queue wait limit and recorded as queue_timed_out."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None
        h.fakes.record_replies[(COMPACTION, 1)] = {"next_step": "not_retried"}
        await h.run_maintenance(COMPACTION)

        assert h.recorded() == [
            (COMPACTION, 1, False, "spark job waited in the queue longer than the queue wait limit")
        ]
        assert h.fakes.records[0]["ended_by"] == "queue_timed_out"
        assert h.fakes.running_records == []
        assert h.fakes.deletes == [FIRST_APP, FIRST_APP]
        assert FIRST_APP in h.fakes.pods_calls
        fenced_at = h.fakes.delete_times[FIRST_APP]
        limit = timedelta(seconds=QUEUE_WAIT_LIMIT_SECONDS)
        assert limit <= fenced_at - h.submit_times()[0] < limit + timedelta(seconds=5)

    _run(scenario)


def test_driver_start_before_submit_is_clamped():
    """A driver clock that reads before the submit starts the deadline at the submit, not earlier."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = (timedelta(0), -timedelta(minutes=10))
        await _run_with_a_short_deadline(h)

        first, second = h.submit_times()
        assert SHORT_DEADLINE <= second - first < SHORT_DEADLINE + timedelta(minutes=3)
        started = datetime.fromisoformat(h.fakes.running_records[0]["started_running_at"])
        assert first <= started < first + timedelta(seconds=5)

    _run(scenario)


def test_failed_running_record_still_starts_the_deadline():
    """A running record that fails is logged; the attempt's deadline still runs from its driver start."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = (QUEUED_FOR, QUEUED_FOR)
        h.fakes.running_record_errors = {(COMPACTION, 1)}
        await _run_with_a_short_deadline(h)

        assert [r["attempt"] for r in h.fakes.running_records] == [1]
        assert h.recorded()[0] == (COMPACTION, 1, False, "spark job timed out")
        first, second = h.submit_times()
        assert QUEUED_FOR + SHORT_DEADLINE <= second - first < QUEUED_FOR + SHORT_DEADLINE + timedelta(minutes=3)

    _run(scenario)


def test_queued_attempt_polls_slowly_after_the_fast_window():
    """A queued attempt polls every 30 s for 10 minutes, then every 10 minutes until the queue wait limit.

    Over the 24 h limit that is at most 20 + (24 h - 10 min) / 10 min = 163 status polls, plus the
    one poll at the limit, which keeps the history of a queued-out attempt small.
    """

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None
        h.fakes.record_replies[(COMPACTION, 1)] = {"next_step": "not_retried"}
        await h.run_maintenance(COMPACTION)

        submitted = h.submit_times()[0]
        polls = [t for t, name in zip(h.fakes.status_times, h.fakes.status_calls, strict=True) if name == FIRST_APP]
        polls = polls[:-AFTER_RUN_CHECK]
        bound = 20 + (timedelta(hours=24) - timedelta(minutes=10)) // timedelta(minutes=10) + 1
        assert len(polls) <= bound
        limit = submitted + timedelta(seconds=QUEUE_WAIT_LIMIT_SECONDS)
        assert len([t for t in polls if t >= limit]) == 1
        polls = [t for t in polls if t < limit]
        gaps = [b - a for a, b in zip(polls, polls[1:], strict=False)]
        late = [g for p, g in zip(polls, gaps, strict=False) if p - submitted >= timedelta(minutes=10)]
        assert late
        assert all(g >= timedelta(minutes=10) for g in late)

    _run(scenario)


def test_fast_poll_window_restarts_at_the_driver_start():
    """After the driver starts, polls run every 30 s again for 10 minutes from that start."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = (timedelta(minutes=30), timedelta(minutes=30))
        await _run_with_a_short_deadline(h)

        started = h.submit_times()[0] + timedelta(minutes=30)
        polls = [t for t, name in zip(h.fakes.status_times, h.fakes.status_calls, strict=True) if name == FIRST_APP]
        window = [t for t in polls if started <= t < started + timedelta(minutes=10)]
        assert len(window) >= 19
        assert all(b - a < timedelta(seconds=60) for a, b in zip(window, window[1:], strict=False))

    _run(scenario)


def test_driver_start_in_the_future_is_clamped_to_now():
    """A driver clock that reads after the poll starts the attempt running at the poll, not later."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = (timedelta(0), timedelta(minutes=10))
        await _run_with_a_short_deadline(h)

        record = h.fakes.running_records[0]
        assert record["started_running_at"] == record["now"]
        first, second = h.submit_times()
        assert SHORT_DEADLINE <= second - first < SHORT_DEADLINE + timedelta(minutes=3)

    _run(scenario)


def test_driver_start_without_a_time_zone_is_read_as_utc():
    """A driver start reported without a time zone is taken as UTC."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = (QUEUED_FOR, QUEUED_FOR)
        h.fakes.naive_driver_starts = {FIRST_APP}
        await _run_with_a_short_deadline(h)

        first, second = h.submit_times()
        assert datetime.fromisoformat(h.fakes.running_records[0]["started_running_at"]) == first + QUEUED_FOR
        assert QUEUED_FOR + SHORT_DEADLINE <= second - first < QUEUED_FOR + SHORT_DEADLINE + timedelta(minutes=3)

    _run(scenario)


REPLACE_ERROR = "queued job could not be replaced: its job was still there 15 minutes after the priority raise"


async def _raise_after(h: Harness, handle: WorkflowHandle, wait: timedelta, priority: str | None = "P0") -> None:
    """Signal a priority raise from the first status poll at least ``wait`` after the first submit.

    The signal goes out from inside that poll, in place of any hook already set, which runs on every
    other poll; its time is kept in ``h.raise_sent_at``. Sending it from the poll, rather than from
    the test after skipping time, keeps the time-skipping server's clock moving only while the test
    awaits the result.
    """
    earlier = h.fakes.status_hook

    async def hook(app_name: str, polled_at: datetime) -> None:
        if h.raise_sent_at is None and polled_at - h.fakes.submitted_at[FIRST_APP] >= wait:
            h.raise_sent_at = polled_at
            await handle.signal(TableMaintenanceSignal.RAISE_PRIORITY, RaisePrioritySignal(priority))
        elif earlier is not None:
            await earlier(app_name, polled_at)

    h.fakes.status_hook = hook


def _succeed_on_raise(h: Harness, operation: str = COMPACTION) -> None:
    """Make a raise send the attempt's success result, as Spark would once the job finished."""

    async def hook(request: dict) -> None:
        await h.client.get_workflow_handle(WORKFLOW_ID).signal(
            TableMaintenanceSignal.OPERATION_RESULT,
            OperationResultSignal(
                run_id=request["run_id"], operation=operation, attempt=1, succeeded=True, metrics={}, error=None
            ),
        )

    h.fakes.raise_hook = hook


def test_raise_requeues_a_queued_attempt():
    """A raise while the attempt is queued deletes its job and, once gone, submits it again under the same attempt.

    The raise comes 15 minutes in, while a queued attempt polls every 10 minutes, and is handled at once.
    """

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None
        h.fakes.vanish_after_delete[FIRST_APP] = timedelta(0)

        async def hook(_: dict) -> None:
            h.fakes.callbacks[(COMPACTION, 1)] = [(1, True, None)]

        h.fakes.raise_hook = hook
        handle = await h.start_maintenance(COMPACTION)
        await _raise_after(h, handle, timedelta(minutes=15))
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert [r["priority"] for r in h.fakes.raises] == ["P0"]
        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [(COMPACTION, 1), (COMPACTION, 1)]
        assert h.recorded() == [(COMPACTION, 1, True, None)]
        commands = await h.commands()
        raised_at = next(at for name, at in commands if name == "raise_maintenance_run_priority")
        assert h.raise_sent_at is not None
        assert h.raise_sent_at - h.submit_times()[0] >= timedelta(minutes=15)
        assert raised_at - h.raise_sent_at < timedelta(minutes=1)
        names = _names(commands)
        raised = names.index("raise_maintenance_run_priority")
        assert names[raised : raised + 6] == [
            "raise_maintenance_run_priority",
            "get_maintenance_job_status",
            "delete_maintenance_job",
            "get_maintenance_job_status",
            "get_maintenance_job_processes",
            "submit_maintenance_operation",
        ]

    _run(scenario)


def test_requeued_attempt_keeps_its_queue_deadline():
    """A requeued attempt is still timed out at the queue wait limit counted from its first submit."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None
        h.fakes.vanish_after_delete[FIRST_APP] = timedelta(0)
        h.fakes.record_replies[(COMPACTION, 1)] = {"next_step": "not_retried"}
        handle = await h.start_maintenance(COMPACTION, queue_wait_limit_seconds=3600)
        await _raise_after(h, handle, timedelta(minutes=30))
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert [r["ended_by"] for r in h.fakes.records] == ["queue_timed_out"]
        first, second = h.submit_times()
        timed_out_at = datetime.fromisoformat(h.fakes.records[0]["now"])
        assert timedelta(hours=1) <= timed_out_at - first < timedelta(hours=1, minutes=1)
        assert second - first >= timedelta(minutes=30)

    _run(scenario)


def test_raise_leaves_a_running_attempt_alone():
    """A raise while the attempt's driver runs records the priority and touches nothing else."""

    async def scenario(h: Harness) -> None:
        _succeed_on_raise(h)
        handle = await h.start_maintenance(COMPACTION)
        await _raise_after(h, handle, timedelta(minutes=1))
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert len(h.fakes.raises) == 1
        assert len(h.fakes.submits) == 1
        assert h.fakes.deletes == [FIRST_APP]
        assert h.recorded() == [(COMPACTION, 1, True, None)]
        assert [r["attempt"] for r in h.fakes.running_records] == [1]
        names = _names(await h.commands())
        raised = names.index("raise_maintenance_run_priority")
        assert "get_maintenance_job_status" not in names[raised : names.index("delete_maintenance_job")]
        assert await h.parent_payloads() == [_report(raises_received=1)]

    _run(scenario)


def test_raise_found_running_at_requeue_time_is_not_requeued():
    """A queued attempt whose driver started by the time of the raise is recorded running, not replaced."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None

        async def hook(_: dict) -> None:
            h.fakes.driver_starts[FIRST_APP] = (timedelta(0), timedelta(seconds=45))
            h.fakes.states[FIRST_APP] = {"state": "COMPLETED", "error": None}

        h.fakes.raise_hook = hook
        handle = await h.start_maintenance(COMPACTION)
        await _raise_after(h, handle, timedelta(minutes=1))
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert len(h.fakes.submits) == 1
        assert h.fakes.deletes == [FIRST_APP]
        assert [r["attempt"] for r in h.fakes.running_records] == [1]
        assert h.recorded() == [(COMPACTION, 1, True, None)]
        assert h.fakes.records[0]["metrics"] == {"completed_without_callback": 1}

    _run(scenario)


def test_next_operation_after_a_raise_submits_after_the_record():
    """A raise is recorded as soon as it arrives, so the next operation is submitted under the raised priority."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(EXPIRE, 1): [(1, True, None)]}
        _succeed_on_raise(h)
        handle = await h.start_maintenance(COMPACTION, EXPIRE)
        await _raise_after(h, handle, timedelta(minutes=1))
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        names = _names(await h.commands())
        raised = names.index("raise_maintenance_run_priority")
        submits = [i for i, name in enumerate(names) if name == "submit_maintenance_operation"]
        assert submits[0] < raised < submits[1]
        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [(COMPACTION, 1), (EXPIRE, 1)]

    _run(scenario)


def test_raise_before_the_first_submit_is_recorded_before_it():
    """A raise that arrives with the workflow's start is recorded before the first submit."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 1): [(1, True, None)]}
        handle = await h.start_maintenance(COMPACTION, raise_at_start=RaisePrioritySignal(None))
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        names = _names(await h.commands())
        assert names.index("raise_maintenance_run_priority") < names.index("submit_maintenance_operation")
        assert h.fakes.raises[0]["priority"] is None
        assert len(h.fakes.submits) == 1

    _run(scenario)


def test_lower_raise_changes_nothing():
    """A raise the run refuses (not above its priority) leaves a queued attempt where it is."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None
        h.fakes.raise_reply = {"priority": "P1", "raised": False}
        _succeed_on_raise(h)
        handle = await h.start_maintenance(COMPACTION)
        await _raise_after(h, handle, timedelta(minutes=1), priority="P3")
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert len(h.fakes.submits) == 1
        assert h.fakes.deletes == [FIRST_APP]
        assert h.recorded() == [(COMPACTION, 1, True, None)]

    _run(scenario)


def test_failed_raise_is_dropped():
    """A raise whose record fails is logged and dropped; the queued attempt is left alone."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None
        h.fakes.raise_errors = {0}
        _succeed_on_raise(h)
        handle = await h.start_maintenance(COMPACTION)
        await _raise_after(h, handle, timedelta(minutes=1))
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert len(h.fakes.raises) == 1
        assert len(h.fakes.submits) == 1
        assert h.fakes.deletes == [FIRST_APP]
        assert (await h.parent_payloads())[0]["unapplied_raise"] is True

    _run(scenario)


def test_queued_job_that_cannot_be_replaced_fails_still_running():
    """A queued job still there 15 minutes after the raise fails the operation as possibly still running."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None
        h.fakes.vanish_after_delete[FIRST_APP] = timedelta(minutes=20)
        h.fakes.callbacks = {(EXPIRE, 1): [(1, True, None)]}
        handle = await h.start_maintenance(COMPACTION, EXPIRE)
        await _raise_after(h, handle, timedelta(minutes=1))
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert h.recorded() == [(COMPACTION, 1, False, REPLACE_ERROR), (EXPIRE, 1, True, None)]
        assert [(r["ended_by"], r["still_running"]) for r in h.fakes.records[:1]] == [("missing", True)]
        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [(COMPACTION, 1), (EXPIRE, 1)]
        deleted_at = h.fakes.delete_times[FIRST_APP]
        assert h.submit_times()[1] - deleted_at >= timedelta(minutes=20)
        polls = [t for t, name in zip(h.fakes.status_times, h.fakes.status_calls, strict=True) if name == FIRST_APP]
        slow = [t for t in polls[:-AFTER_RUN_CHECK] if t - deleted_at >= timedelta(minutes=15)]
        assert all(b - a >= timedelta(minutes=5) for a, b in itertools.pairwise(slow))

    _run(scenario)


def _succeed_on_the_status_read_after_the_raise(h: Harness) -> None:
    """Send the attempt's success result from the first status read after a raise, once that read answered."""
    sent: list[bool] = []

    async def hook(_: str, __: datetime) -> None:
        if h.fakes.raises and not sent:
            sent.append(True)
            await h.client.get_workflow_handle(WORKFLOW_ID).signal(
                TableMaintenanceSignal.OPERATION_RESULT,
                OperationResultSignal(
                    run_id=RUN_IDS[0], operation=COMPACTION, attempt=1, succeeded=True, metrics={}, error=None
                ),
            )

    h.fakes.status_hook = hook


def test_raise_while_running_without_a_driver_start_is_not_requeued():
    """A job that reads RUNNING is not replaced even when its driver start could not be read."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None
        h.fakes.states[FIRST_APP] = {"state": "RUNNING", "error": None}
        _succeed_on_the_status_read_after_the_raise(h)
        handle = await h.start_maintenance(COMPACTION)
        await _raise_after(h, handle, timedelta(minutes=1))
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert len(h.fakes.raises) == 1
        assert len(h.fakes.submits) == 1
        assert h.fakes.deletes == [FIRST_APP]
        assert h.recorded() == [(COMPACTION, 1, True, None)]

    _run(scenario)


def test_raise_while_the_job_failed_records_the_failure():
    """A raise that finds the queued job failed ends the attempt as job_failed; nothing is submitted again."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None
        h.fakes.record_replies[(COMPACTION, 1)] = {"next_step": "not_retried"}

        async def hook(_: dict) -> None:
            h.fakes.states[FIRST_APP] = {"state": "FAILED", "error": "driver could not be scheduled"}

        h.fakes.raise_hook = hook
        handle = await h.start_maintenance(COMPACTION)
        await _raise_after(h, handle, timedelta(minutes=1))
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert h.recorded() == [(COMPACTION, 1, False, "driver could not be scheduled")]
        assert h.fakes.records[0]["ended_by"] == "job_failed"
        assert len(h.fakes.submits) == 1
        assert h.fakes.deletes == [FIRST_APP]

    _run(scenario)


def test_requeue_waits_for_the_next_poll_when_the_status_is_unknown():
    """A raise whose status read fails is requeued at the next poll that reads the job still pending."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None
        h.fakes.vanish_after_delete[FIRST_APP] = timedelta(0)
        failed: list[bool] = []

        async def on_status(_: str, __: datetime) -> None:
            if h.fakes.raises and not failed:
                failed.append(True)
                raise ApplicationError("apiserver unavailable", type="RuntimeError", non_retryable=True)

        async def on_raise(_: dict) -> None:
            h.fakes.callbacks[(COMPACTION, 1)] = [(1, True, None)]

        h.fakes.status_hook = on_status
        h.fakes.raise_hook = on_raise
        handle = await h.start_maintenance(COMPACTION)
        await _raise_after(h, handle, timedelta(minutes=15))
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        commands = await h.commands()
        names = _names(commands)
        raised = names.index("raise_maintenance_run_priority")
        assert names[raised : raised + 7] == [
            "raise_maintenance_run_priority",
            "get_maintenance_job_status",
            "get_maintenance_job_status",
            "delete_maintenance_job",
            "get_maintenance_job_status",
            "get_maintenance_job_processes",
            "submit_maintenance_operation",
        ]
        unknown_at, next_poll_at = commands[raised + 1][1], commands[raised + 2][1]
        assert next_poll_at - unknown_at >= timedelta(minutes=4)
        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [(COMPACTION, 1), (COMPACTION, 1)]

    _run(scenario)


def _submitting_on_raise(h: Harness, reads: int) -> list[datetime]:
    """Make the job read ``SUBMITTING`` from the raise for ``reads`` status reads, then pending; return their times."""
    seen: list[datetime] = []

    async def on_raise(_: dict) -> None:
        h.fakes.states[FIRST_APP] = {"state": "SUBMITTING", "error": None}
        h.fakes.callbacks[(COMPACTION, 1)] = [(1, True, None)]

    async def on_status(app_name: str, at: datetime) -> None:
        state = h.fakes.states.get(app_name)
        if not isinstance(state, dict) or state.get("state") != "SUBMITTING":
            return
        if len(seen) == reads:
            h.fakes.states.pop(app_name)
        else:
            seen.append(at)

    h.fakes.raise_hook = on_raise
    h.fakes.status_hook = on_status
    return seen


def test_raise_waits_for_a_job_still_being_submitted():
    """A job the cluster is still submitting is not replaced: read again 5 s later, it is replaced once pending.

    Replacing it then would let the submit still under way create a coordinator under the replacement's
    name, and the replacement's own submit would fail on it.
    """

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None
        h.fakes.vanish_after_delete[FIRST_APP] = timedelta(0)
        submitting = _submitting_on_raise(h, reads=2)
        handle = await h.start_maintenance(COMPACTION)
        await _raise_after(h, handle, timedelta(minutes=1))
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        commands = await h.commands()
        names = _names(commands)
        raised = names.index("raise_maintenance_run_priority")
        assert names[raised : raised + 8] == [
            "raise_maintenance_run_priority",
            "get_maintenance_job_status",
            "get_maintenance_job_status",
            "get_maintenance_job_status",
            "delete_maintenance_job",
            "get_maintenance_job_status",
            "get_maintenance_job_processes",
            "submit_maintenance_operation",
        ]
        reads = [at for _, at in commands[raised + 1 : raised + 4]]
        gaps = [later - earlier for earlier, later in itertools.pairwise(reads)]
        assert all(timedelta(seconds=5) <= gap < timedelta(seconds=6) for gap in gaps), gaps
        assert len(submitting) == 2
        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [(COMPACTION, 1), (COMPACTION, 1)]
        assert h.recorded() == [(COMPACTION, 1, True, None)]

    _run(scenario)


def test_raise_on_a_job_submitting_long_after_its_submit_polls_at_the_queued_pace():
    """Past the fast window a job still being submitted is read at the queued pace, so a stuck submit stays cheap."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None
        h.fakes.vanish_after_delete[FIRST_APP] = timedelta(0)
        _submitting_on_raise(h, reads=1)
        handle = await h.start_maintenance(COMPACTION)
        await _raise_after(h, handle, timedelta(minutes=15))
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        commands = await h.commands()
        names = _names(commands)
        raised = names.index("raise_maintenance_run_priority")
        assert names[raised : raised + 4] == [
            "raise_maintenance_run_priority",
            "get_maintenance_job_status",
            "get_maintenance_job_status",
            "delete_maintenance_job",
        ]
        gap = commands[raised + 2][1] - commands[raised + 1][1]
        assert timedelta(minutes=10) <= gap < timedelta(minutes=10, seconds=1), gap
        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [(COMPACTION, 1), (COMPACTION, 1)]

    _run(scenario)


def test_a_second_raise_on_a_replacement_still_being_submitted_is_read_again_in_5_s():
    """The fast window runs from the latest submit, so a raise right after a requeue is not held 10 minutes.

    The first raise, 15 minutes into the queue wait, replaces the pending job. A second raise
    arrives while the replacement is being submitted and finds it still ``SUBMITTING``: it is read
    again 5 s later, as a raise on a fresh job is, and replaced once it reads pending.
    """

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None
        h.fakes.vanish_after_delete[FIRST_APP] = timedelta(0)
        handle = await h.start_maintenance(COMPACTION)
        submitting_reads: list[datetime] = []

        async def on_submit(_: dict) -> None:
            if len(h.fakes.submits) == 2:
                h.fakes.states[FIRST_APP] = {"state": "SUBMITTING", "error": None}
                await handle.signal(TableMaintenanceSignal.RAISE_PRIORITY, RaisePrioritySignal("P0"))
            elif len(h.fakes.submits) == 3:
                h.fakes.callbacks[(COMPACTION, 1)] = [(1, True, None)]

        async def on_status(app_name: str, at: datetime) -> None:
            if h.fakes.states.get(app_name) == {"state": "SUBMITTING", "error": None}:
                submitting_reads.append(at)
                if len(submitting_reads) == 2:
                    h.fakes.states.pop(app_name)

        h.fakes.submit_hook = on_submit
        h.fakes.status_hook = on_status
        await _raise_after(h, handle, timedelta(minutes=15), priority="P1")
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [(COMPACTION, 1)] * 3
        assert len(submitting_reads) == 2
        assert timedelta(seconds=5) <= submitting_reads[1] - submitting_reads[0] < timedelta(seconds=6), (
            submitting_reads
        )
        assert h.recorded() == [(COMPACTION, 1, True, None)]

    _run(scenario)


def test_finish_reports_a_raise_left_unapplied():
    """A raise that arrives after the last operation was awaited is reported to the parent as unapplied."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 1): [(1, True, None)]}

        async def hook(_: dict) -> None:
            await h.client.get_workflow_handle(WORKFLOW_ID).signal(
                TableMaintenanceSignal.RAISE_PRIORITY, RaisePrioritySignal("P0")
            )

        h.fakes.record_hook = hook
        await h.run_maintenance(COMPACTION)

        assert h.fakes.raises == []
        assert await h.parent_payloads() == [_report(unapplied_raise=True, raises_received=1)]

    _run(scenario)


def test_raise_interrupted_by_a_cancel_is_reported_unapplied():
    """A raise whose record a cancel interrupted is reported to the parent as unapplied."""

    async def scenario(h: Harness) -> None:
        gate = asyncio.Event()

        async def hook(_: dict) -> None:
            await gate.wait()

        h.fakes.raise_hook = hook
        handle = await h.start_maintenance(COMPACTION)
        try:
            await _raise_after(h, handle, timedelta(minutes=1))
            result = asyncio.ensure_future(handle.result())
            await eventually(lambda: _value(len(h.fakes.raises)), lambda n: n == 1)
            await handle.cancel()
            with pytest.raises(WorkflowFailureError):
                await asyncio.wait_for(result, timeout=REAL_TIMEOUT_SECONDS)
        finally:
            gate.set()
        assert (await h.parent_payloads())[0]["unapplied_raise"] is True

    _run(scenario)


def test_result_during_the_raise_poll_is_not_requeued():
    """A result that arrives while the poll after a raise runs wins; the pending job is not replaced."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None
        h.fakes.vanish_after_delete[FIRST_APP] = timedelta(0)
        _succeed_on_the_status_read_after_the_raise(h)
        handle = await h.start_maintenance(COMPACTION)
        await _raise_after(h, handle, timedelta(minutes=1))
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert len(h.fakes.submits) == 1
        assert h.fakes.deletes == [FIRST_APP]
        assert h.recorded() == [(COMPACTION, 1, True, None)]

    _run(scenario)


SHORT_QUEUE_LIMIT = timedelta(hours=1)


def test_driver_start_read_at_the_queue_limit_runs_the_attempt():
    """A driver start first reported by the poll at the queue wait limit makes the attempt run, not time out.

    Every poll before the limit reads the job pending; the one at the limit reads the start, so the
    attempt runs under its deadline from that start and its result is recorded.
    """

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = (SHORT_QUEUE_LIMIT, SHORT_QUEUE_LIMIT)

        async def succeed_once_running(app_name: str, _: datetime) -> None:
            if app_name == FIRST_APP and h.fakes.running_records and not h.fakes.callbacks:
                h.fakes.callbacks[(COMPACTION, 1)] = [(1, True, None)]
                await h.client.get_workflow_handle(WORKFLOW_ID).signal(
                    TableMaintenanceSignal.OPERATION_RESULT,
                    OperationResultSignal(RUN_IDS[0], COMPACTION, 1, True, {"files": 4}, None),
                )

        h.fakes.status_hook = succeed_once_running
        handle = await h.start_maintenance(COMPACTION, queue_wait_limit_seconds=int(SHORT_QUEUE_LIMIT.total_seconds()))
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert h.recorded() == [(COMPACTION, 1, True, None)]
        assert len(h.fakes.submits) == 1
        [running] = h.fakes.running_records
        assert datetime.fromisoformat(running["started_running_at"]) == h.submit_times()[0] + SHORT_QUEUE_LIMIT
        assert h.fakes.deletes == [FIRST_APP]

    _run(scenario)


def test_still_pending_at_the_queue_limit_is_polled_once_then_fenced():
    """At the queue wait limit a job is polled once more; still pending without a start, it is fenced."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None
        h.fakes.record_replies[(COMPACTION, 1)] = {"next_step": "not_retried"}
        handle = await h.start_maintenance(COMPACTION, queue_wait_limit_seconds=int(SHORT_QUEUE_LIMIT.total_seconds()))
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert [r["ended_by"] for r in h.fakes.records] == ["queue_timed_out"]
        limit = h.submit_times()[0] + SHORT_QUEUE_LIMIT
        commands = await h.commands()
        delete = _names(commands).index("delete_maintenance_job")
        last_poll = max(i for i, (name, _) in enumerate(commands[:delete]) if name == "get_maintenance_job_status")
        assert commands[last_poll][1] >= limit

    _run(scenario)


def test_late_result_of_the_replaced_job_is_dropped():
    """A result the killed job sends while a requeue deletes it is dropped; the replacement's result is recorded."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None
        h.fakes.vanish_after_delete[FIRST_APP] = timedelta(0)
        sent: list[bool] = []

        async def killed_job_reports(app_name: str) -> None:
            if app_name == FIRST_APP and not sent:
                sent.append(True)
                await h.client.get_workflow_handle(WORKFLOW_ID).signal(
                    TableMaintenanceSignal.OPERATION_RESULT,
                    OperationResultSignal(RUN_IDS[0], COMPACTION, 1, False, {}, "driver killed by the delete"),
                )

        async def replacement_succeeds(_: dict) -> None:
            h.fakes.callbacks[(COMPACTION, 1)] = [(1, True, None)]

        h.fakes.delete_hook = killed_job_reports
        h.fakes.raise_hook = replacement_succeeds
        handle = await h.start_maintenance(COMPACTION)
        await _raise_after(h, handle, timedelta(minutes=15))
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert sent == [True]
        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [(COMPACTION, 1), (COMPACTION, 1)]
        assert h.recorded() == [(COMPACTION, 1, True, None)]

    _run(scenario)


def _state_from_the_queue_limit(h: Harness, state: dict) -> None:
    """Make every status poll from the queue wait limit on read ``state``, with no driver start to read."""

    async def hook(app_name: str, polled_at: datetime) -> None:
        if app_name == FIRST_APP and polled_at - h.fakes.submitted_at[FIRST_APP] >= SHORT_QUEUE_LIMIT:
            h.fakes.states[FIRST_APP] = state

    h.fakes.status_hook = hook


def test_completed_at_the_queue_limit_without_a_readable_start_succeeds():
    """A job read COMPLETED at the queue limit, its driver start unreadable, is taken as started then and succeeds.

    It gets its callback grace like any completed job instead of being fenced as queued too long.
    """

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None
        _state_from_the_queue_limit(h, {"state": "COMPLETED", "error": None})
        handle = await h.start_maintenance(COMPACTION, queue_wait_limit_seconds=int(SHORT_QUEUE_LIMIT.total_seconds()))
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert h.recorded() == [(COMPACTION, 1, True, None)]
        assert h.fakes.records[0]["metrics"] == {"completed_without_callback": 1}
        [running] = h.fakes.running_records
        assert running["started_running_at"] == running["now"]
        assert len(h.fakes.submits) == 1

    _run(scenario)


def test_running_at_the_queue_limit_without_a_readable_start_runs_under_its_deadline():
    """A job read RUNNING at the queue limit, its driver start unreadable, is taken as started then.

    It runs under its deadline from that poll and is timed out (not queue timed out) at it.
    """

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None
        h.fakes.record_replies[(COMPACTION, 1)] = {"next_step": "not_retried"}
        _state_from_the_queue_limit(h, {"state": "RUNNING", "error": None})
        handle = await h.start_maintenance(
            COMPACTION,
            queue_wait_limit_seconds=int(SHORT_QUEUE_LIMIT.total_seconds()),
            attempt_deadline_seconds=int(SHORT_DEADLINE.total_seconds()),
        )
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert [r["ended_by"] for r in h.fakes.records] == ["timed_out"]
        [running] = h.fakes.running_records
        started = datetime.fromisoformat(running["started_running_at"])
        assert started - h.submit_times()[0] >= SHORT_QUEUE_LIMIT
        timed_out_at = datetime.fromisoformat(h.fakes.records[0]["now"])
        assert timed_out_at - started >= SHORT_DEADLINE

    _run(scenario)


STOPPED_BEFORE_IT_STARTED = "the table's maintenance stopped before this run started"


def _app(run: int, operation: str, attempt: int = 1) -> str:
    """Return the Spark application name of an attempt of the ``run``-th run (from 0) of the plan."""
    return ScriptedMaintenanceActivities.app_name(RUN_IDS[run], operation, attempt)


def test_each_operation_runs_as_its_own_run():
    """Every planned operation runs as the run the parent named for it, its submit carrying no parameters of its own."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 1): [(1, True, None)], (EXPIRE, 1): [(1, True, None)]}
        await h.run_maintenance(COMPACTION, EXPIRE)
        assert "content" not in h.fakes.submits[0]
        assert [(s["run_id"], s["operation"]) for s in h.fakes.submits] == [
            (RUN_IDS[0], COMPACTION),
            (RUN_IDS[1], EXPIRE),
        ]
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:2]))]

    _run(scenario)


def test_the_next_run_submits_only_after_the_previous_run_ended():
    """A run's first submit comes after the previous run's last attempt was recorded and its job deleted."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 1): [(1, True, None)], (EXPIRE, 1): [(1, True, None)]}
        await h.run_maintenance(COMPACTION, EXPIRE)
        names = [name for name, _ in await h.commands()]
        second_submit = [i for i, n in enumerate(names) if n == "submit_maintenance_operation"][1]
        assert (
            names.index("record_maintenance_operation_result") < names.index("delete_maintenance_job") < second_submit
        )

    _run(scenario)


def test_a_failed_run_does_not_stop_the_next():
    """A run that fails for good is recorded, and the next run still runs; nothing is skipped."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 1): [(1, False, "boom")], (EXPIRE, 1): [(1, True, None)]}
        h.fakes.record_replies = {(COMPACTION, 1): {"next_step": "not_retried"}}
        await h.run_maintenance(COMPACTION, EXPIRE)

        assert h.recorded() == [(COMPACTION, 1, False, "boom"), (EXPIRE, 1, True, None)]
        assert [(s["run_id"], s["attempt"]) for s in h.fakes.submits] == [(RUN_IDS[0], 1), (RUN_IDS[1], 1)]
        assert h.fakes.skips == []
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:2]))]

    _run(scenario)


def test_a_submit_failure_fails_its_run_and_the_next_run_still_runs():
    """A run whose every submit fails ends failed; the workflow goes on to the next run, then reports.

    No submit of the first run returned, so the workflow cannot tell whether that run ever left pending; it asks
    for a skip at the end, which leaves a run that did start (here: failed) as it is.
    """

    async def scenario(h: Harness) -> None:
        h.fakes.submit_errors = {(COMPACTION, a): "k8s down" for a in (1, 2, 3)}
        h.fakes.callbacks = {(EXPIRE, 1): [(1, True, None)]}
        await h.run_maintenance(COMPACTION, EXPIRE)

        assert h.recorded() == [
            (COMPACTION, 1, False, "submit failed: k8s down"),
            (COMPACTION, 2, False, "submit failed: k8s down"),
            (COMPACTION, 3, False, "submit failed: k8s down"),
            (EXPIRE, 1, True, None),
        ]
        assert [s["run_id"] for s in h.fakes.skips] == [RUN_IDS[0]]
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:2]))]

    _run(scenario)


def test_runs_never_reached_are_skipped_when_the_workflow_is_cancelled():
    """A cancel during the first run skips the runs after it, saying why, and the parent still gets the report."""

    async def scenario(h: Harness) -> None:
        gate = h.fakes.status_gate = asyncio.Event()
        await _cancel_while_blocked(
            h,
            gate,
            lambda: len(h.fakes.status_calls) == 1,
            advance=timedelta(seconds=31),
            operations=(COMPACTION, EXPIRE, ORPHANS),
        )
        assert [s["run_id"] for s in h.fakes.skips] == [RUN_IDS[1], RUN_IDS[2]]
        assert {s["reason"] for s in h.fakes.skips} == {STOPPED_BEFORE_IT_STARTED}
        names = _names(await h.commands())
        assert max(i for i, n in enumerate(names) if n == "skip_maintenance_run") < names.index("signal_parent")

    _run(scenario)


def test_a_result_naming_another_runs_id_is_dropped():
    """A result for the first run's operation that names the second run's id is dropped; the first run's own counts."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(EXPIRE, 1): [(1, True, None)]}
        handle = await h.start_maintenance(COMPACTION, EXPIRE)
        await eventually(lambda: _value(len(h.fakes.submits)), lambda n: n == 1)
        await handle.signal(
            TableMaintenanceSignal.OPERATION_RESULT,
            OperationResultSignal(RUN_IDS[1], COMPACTION, 1, False, {}, "for another run"),
        )
        await handle.signal(
            TableMaintenanceSignal.OPERATION_RESULT,
            OperationResultSignal(RUN_IDS[0], COMPACTION, 1, True, {"files": 5}, None),
        )
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert h.recorded() == [(COMPACTION, 1, True, None), (EXPIRE, 1, True, None)]
        assert [r["run_id"] for r in h.fakes.records] == [RUN_IDS[0], RUN_IDS[1]]
        assert h.fakes.records[0]["metrics"] == {"files": 5}

    _run(scenario)


def test_a_raise_reaches_every_run_not_finished():
    """A raise while the first of three runs is queued raises all three; only the first run's attempt is requeued."""

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None
        h.fakes.vanish_after_delete[FIRST_APP] = timedelta(0)
        h.fakes.callbacks = {(EXPIRE, 1): [(1, True, None)], (ORPHANS, 1): [(1, True, None)]}

        async def hook(_: dict) -> None:
            h.fakes.callbacks[(COMPACTION, 1)] = [(1, True, None)]

        h.fakes.raise_hook = hook
        handle = await h.start_maintenance(COMPACTION, EXPIRE, ORPHANS)
        await _raise_after(h, handle, timedelta(minutes=15), priority="P1")
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert [(r["run_id"], r["priority"]) for r in h.fakes.raises] == [(r, "P1") for r in RUN_IDS[:3]]
        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [
            (COMPACTION, 1),
            (COMPACTION, 1),
            (EXPIRE, 1),
            (ORPHANS, 1),
        ]
        assert h.fakes.submitted_priorities == ["P3", "P1", "P1", "P1"]
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:3]), raises_received=1)]

    _run(scenario)


def test_only_the_current_runs_reply_decides_the_requeue():
    """A raise the current run refuses leaves its queued attempt alone, even when the run after it took it.

    The current run's attempt is still queued (no driver start) when the raise arrives; its result is
    sent from a status poll at least a minute after the raise, so a requeue, which polls at once,
    would delete and resubmit that attempt first.
    """

    async def scenario(h: Harness) -> None:
        h.fakes.driver_starts[FIRST_APP] = None
        h.fakes.vanish_after_delete[FIRST_APP] = timedelta(0)
        h.fakes.callbacks = {(EXPIRE, 1): [(1, True, None)]}

        async def reply(request: dict) -> None:
            current = request["run_id"] == RUN_IDS[0]
            h.fakes.raise_reply = {"priority": "P1", "raised": False} if current else None

        async def finish_after_the_raise(_: str, polled_at: datetime) -> None:
            if h.raise_sent_at is not None and polled_at - h.raise_sent_at >= timedelta(minutes=1):
                await h.client.get_workflow_handle(WORKFLOW_ID).signal(
                    TableMaintenanceSignal.OPERATION_RESULT,
                    OperationResultSignal(RUN_IDS[0], COMPACTION, 1, True, {}, None),
                )

        h.fakes.raise_hook = reply
        h.fakes.status_hook = finish_after_the_raise
        handle = await h.start_maintenance(COMPACTION, EXPIRE)
        await _raise_after(h, handle, timedelta(minutes=15), priority="P2")
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert [r["run_id"] for r in h.fakes.raises] == list(RUN_IDS[:2])
        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [(COMPACTION, 1), (EXPIRE, 1)]
        assert h.fakes.submitted_priorities == ["P3", "P2"]
        assert h.recorded() == [(COMPACTION, 1, True, None), (EXPIRE, 1, True, None)]

    _run(scenario)


def test_a_failed_raise_of_a_later_run_is_reported_unapplied():
    """A raise that fails for the third run is reported to the parent as left unapplied."""

    async def scenario(h: Harness) -> None:
        h.fakes.raise_errors = {2}
        h.fakes.callbacks = {(EXPIRE, 1): [(1, True, None)], (ORPHANS, 1): [(1, True, None)]}
        _succeed_on_raise(h)
        handle = await h.start_maintenance(COMPACTION, EXPIRE, ORPHANS)
        await _raise_after(h, handle, timedelta(minutes=1))
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert [r["run_id"] for r in h.fakes.raises] == list(RUN_IDS[:3])
        assert h.recorded() == [(COMPACTION, 1, True, None), (EXPIRE, 1, True, None), (ORPHANS, 1, True, None)]
        assert await h.parent_payloads() == [
            _report(run_ids=list(RUN_IDS[:3]), unapplied_raise=True, raises_received=1)
        ]

    _run(scenario)


def test_a_raise_during_the_retry_backoff_reaches_the_retry():
    """A raise that arrives while run 1's failed attempt waits out its backoff reaches the retry and runs 2 and 3.

    It is applied before the retry is submitted, and the later runs are submitted at the raised priority.
    """

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {
            (COMPACTION, 1): [(1, False, "boom")],
            (COMPACTION, 2): [(2, True, None)],
            (EXPIRE, 1): [(1, True, None)],
            (ORPHANS, 1): [(1, True, None)],
        }

        async def hook(request: dict) -> None:
            if (request["operation"], request["attempt"]) == (COMPACTION, 1):
                await h.client.get_workflow_handle(WORKFLOW_ID).signal(
                    TableMaintenanceSignal.RAISE_PRIORITY, RaisePrioritySignal("P1")
                )

        h.fakes.record_hook = hook
        await h.run_maintenance(COMPACTION, EXPIRE, ORPHANS)

        assert [(r["run_id"], r["priority"]) for r in h.fakes.raises] == [(run, "P1") for run in RUN_IDS[:3]]
        names = _names(await h.commands())
        submits = [i for i, n in enumerate(names) if n == "submit_maintenance_operation"]
        raises = [i for i, n in enumerate(names) if n == "raise_maintenance_run_priority"]
        assert names.index("record_maintenance_operation_result") < raises[0]
        assert raises[-1] < submits[1]
        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [
            (COMPACTION, 1),
            (COMPACTION, 2),
            (EXPIRE, 1),
            (ORPHANS, 1),
        ]
        assert h.fakes.submitted_priorities == ["P3", "P1", "P1", "P1"]
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:3]), raises_received=1)]

    _run(scenario)


def test_the_jobs_of_a_run_are_deleted_when_it_ends():
    """Each run's job is deleted once that run ended, and none is deleted again when the workflow finishes."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 1): [(1, True, None)], (EXPIRE, 1): [(1, True, None)]}
        await h.run_maintenance(COMPACTION, EXPIRE)

        assert h.fakes.deletes == [_app(0, COMPACTION), _app(1, EXPIRE)]
        names = _names(await h.commands())
        deletes = [i for i, n in enumerate(names) if n == "delete_maintenance_job"]
        expire_submit = [i for i, n in enumerate(names) if n == "submit_maintenance_operation"][1]
        assert deletes[0] < expire_submit < deletes[1]

    _run(scenario)


def test_an_early_result_for_a_later_run_is_dropped():
    """A result for run 2 that arrives while run 1 runs is dropped; run 2's attempt ends with its own result.

    Run 2's attempt has not started when the early result arrives, so keeping it would end that attempt
    as soon as it is submitted, with the early result's outcome.
    """

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(EXPIRE, 1): [(1, True, None)]}
        handle = await h.start_maintenance(COMPACTION, EXPIRE)
        await eventually(lambda: _value(len(h.fakes.submits)), lambda n: n == 1)
        await handle.signal(
            TableMaintenanceSignal.OPERATION_RESULT,
            OperationResultSignal(RUN_IDS[1], EXPIRE, 1, False, {}, "too early"),
        )
        await handle.signal(
            TableMaintenanceSignal.OPERATION_RESULT,
            OperationResultSignal(RUN_IDS[0], COMPACTION, 1, True, {"files": 5}, None),
        )
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)

        assert h.recorded() == [(COMPACTION, 1, True, None), (EXPIRE, 1, True, None)]
        assert h.fakes.records[1]["metrics"] == {"files": 1}

    _run(scenario)


def test_a_cancel_before_any_submit_returned_skips_every_run_of_the_plan():
    """A cancel while the first submit is in flight skips every run of the plan: the parent created them all."""

    async def scenario(h: Harness) -> None:
        gate = h.fakes.submit_gate = asyncio.Event()
        handle = await h.start_maintenance(COMPACTION, EXPIRE, ORPHANS)
        try:
            await eventually(lambda: _value(len(h.fakes.submits)), lambda n: n == 1)
            await handle.cancel()
            with pytest.raises(WorkflowFailureError) as caught:
                await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)
        finally:
            gate.set()

        assert isinstance(caught.value.cause, CancelledError)
        assert [s["run_id"] for s in h.fakes.skips] == list(RUN_IDS[:3])
        assert {s["reason"] for s in h.fakes.skips} == {STOPPED_BEFORE_IT_STARTED}
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:3]))]

    _run(scenario)


def test_a_skip_that_finds_no_run_is_only_logged():
    """A skip at the end that fails, a run not found included, is logged, and the parent still gets the report."""

    async def scenario(h: Harness) -> None:
        gate = h.fakes.submit_gate = asyncio.Event()
        h.fakes.skip_errors = {RUN_IDS[0]}
        handle = await h.start_maintenance(COMPACTION, EXPIRE)
        try:
            await eventually(lambda: _value(len(h.fakes.submits)), lambda n: n == 1)
            await handle.cancel()
            with pytest.raises(WorkflowFailureError) as caught:
                await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)
        finally:
            gate.set()

        assert isinstance(caught.value.cause, CancelledError)
        assert [s["run_id"] for s in h.fakes.skips] == list(RUN_IDS[:2])
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:2]))]

    _run(scenario)


def test_a_submit_refused_before_its_attempt_started_skips_the_run_with_the_refusal():
    """A submit refused before it saved the attempt leaves the run pending: it is skipped with the refusal, not retried.

    The record answers that the run is still pending, so the workflow counts no record failure, submits that run
    no more, skips it saying what the submit refused, and goes on to the next run.
    """

    async def scenario(h: Harness) -> None:
        h.fakes.submit_errors = {(COMPACTION, 1): "table u1 not found"}
        h.fakes.record_replies = {(COMPACTION, 1): {"status": "pending"}}
        h.fakes.callbacks = {(EXPIRE, 1): [(1, True, None)]}
        await h.run_maintenance(COMPACTION, EXPIRE)

        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [(COMPACTION, 1), (EXPIRE, 1)]
        assert [(s["run_id"], s["reason"]) for s in h.fakes.skips] == [
            (RUN_IDS[0], "submit failed: table u1 not found")
        ]
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:2]))]

    _run(scenario)


JOB_STAYS = timedelta(minutes=3)
PODS_STAY = timedelta(minutes=1)


def test_the_next_run_submits_only_once_the_previous_runs_job_is_gone():
    """Run 2 is submitted only once run 1's job reads ``NOT_FOUND`` and has no live pods, not at its delete.

    A foreground delete leaves the SparkApplication in place, its driver being killed, until its pods are
    gone, and only one Spark job of a table may exist at a time. The job here outlives its pods.
    """

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 1): [(1, True, None)], (EXPIRE, 1): [(1, True, None)]}
        h.fakes.vanish_after_delete[FIRST_APP] = JOB_STAYS
        h.fakes.pods_live_for[FIRST_APP] = PODS_STAY
        await h.run_maintenance(COMPACTION, EXPIRE)

        deleted_at = h.fakes.delete_times[FIRST_APP]
        expire_submitted_at = h.submit_times()[1]
        assert expire_submitted_at - deleted_at >= JOB_STAYS
        polls = [at for app, at in zip(h.fakes.status_calls, h.fakes.status_times, strict=True) if app == FIRST_APP]
        assert any(deleted_at + JOB_STAYS <= at <= expire_submitted_at for at in polls)
        assert h.recorded() == [(COMPACTION, 1, True, None), (EXPIRE, 1, True, None)]
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:2]))]

    _run(scenario)


def test_the_workflow_reports_only_once_the_last_runs_job_is_gone():
    """The last run's job is gone before the parent is told, so the next plan's first job cannot overlap it."""

    async def scenario(h: Harness) -> None:
        h.fakes.callbacks = {(COMPACTION, 1): [(1, True, None)]}
        h.fakes.vanish_after_delete[FIRST_APP] = JOB_STAYS
        await h.run_maintenance(COMPACTION)

        commands = await h.commands()
        report = _first_after(commands, "signal_parent", 0)
        assert commands[report][1] - h.fakes.delete_times[FIRST_APP] >= JOB_STAYS
        assert h.fakes.deletes == [FIRST_APP]

    _run(scenario)


def test_a_cancelled_workflow_reports_only_once_every_job_of_its_run_is_gone():
    """A cancel during attempt 2 waits, before the report, until attempt 1's job is gone too, as the fence waits."""

    async def scenario(h: Harness) -> None:
        second = _app(0, COMPACTION, 2)
        h.fakes.callbacks = {(COMPACTION, 1): [(1, False, "boom")]}
        h.fakes.vanish_after_delete[FIRST_APP] = JOB_STAYS
        cancelled: list[bool] = []

        async def cancel(app_name: str, _scheduled: datetime) -> None:
            if app_name == second and not cancelled:
                await _cancel_inside_the_activity(h, cancelled)

        h.fakes.status_hook = cancel
        handle = await h.start_maintenance(COMPACTION, EXPIRE)
        with pytest.raises(WorkflowFailureError):
            await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)
        assert cancelled == [True]

        commands = await h.commands()
        report = _first_after(commands, "signal_parent", 0)
        assert commands[report][1] - h.fakes.delete_times[FIRST_APP] >= JOB_STAYS
        assert h.recorded() == [(COMPACTION, 1, False, "boom"), (COMPACTION, 2, False, "cancelled")]

    _run(scenario)


async def _waits_out_a_backoff(h: Harness) -> bool:
    """Tell whether the workflow started a timer after it recorded its latest attempt: the backoff before a retry."""
    history = await h.client.get_workflow_handle(WORKFLOW_ID).fetch_history()
    events = list(history.events)
    records = [
        i
        for i, event in enumerate(events)
        if event.HasField("activity_task_scheduled_event_attributes")
        and event.activity_task_scheduled_event_attributes.activity_type.name == "record_maintenance_operation_result"
    ]
    return bool(records) and any(event.HasField("timer_started_event_attributes") for event in events[records[-1] :])


async def _cancel_during_the_retry_wait(h: Harness) -> None:
    """Fail run 1's first attempt with a retry to follow, and cancel the workflow while it waits to retry."""
    h.fakes.callbacks = {(COMPACTION, 1): [(1, False, "boom")]}
    h.fakes.record_replies = {
        (COMPACTION, 1): {"status": "retry_waiting", "failure_class": "other", "next_step": "retry_same"},
    }
    handle = await h.start_maintenance(COMPACTION, EXPIRE)
    await eventually(lambda: _waits_out_a_backoff(h), bool, timeout=REAL_TIMEOUT_SECONDS)
    await handle.cancel()
    with pytest.raises(WorkflowFailureError) as caught:
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)
    assert isinstance(caught.value.cause, CancelledError)


def test_a_cancel_during_the_retry_wait_cancels_the_run():
    """A cancel while run 1 waits to retry cancels that run, which has no attempt in flight to record.

    No attempt follows, the run never reached is skipped, and the parent is told as after any cancel.
    """

    async def scenario(h: Harness) -> None:
        await _cancel_during_the_retry_wait(h)

        assert [c["run_id"] for c in h.fakes.cancels] == [RUN_IDS[0]]
        assert h.recorded() == [(COMPACTION, 1, False, "boom")]
        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [(COMPACTION, 1)]
        assert [s["run_id"] for s in h.fakes.skips] == [RUN_IDS[1]]
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:2]))]
        names = _names(await h.commands())
        assert names.index("cancel_maintenance_run") < names.index("signal_parent")

    _run(scenario)


def test_a_failed_cancel_during_the_retry_wait_still_ends_the_workflow():
    """A cancel of the waiting run that fails is logged: the workflow still ends cancelled and tells the parent."""

    async def scenario(h: Harness) -> None:
        h.fakes.cancel_errors = {RUN_IDS[0]}
        await _cancel_during_the_retry_wait(h)

        assert [c["run_id"] for c in h.fakes.cancels] == [RUN_IDS[0]]
        assert [s["run_id"] for s in h.fakes.skips] == [RUN_IDS[1]]
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:2]))]

    _run(scenario)


async def _cancel_reached_the_workflow(h: Harness) -> bool:
    """Tell whether the workflow finished a workflow task after the cancel request: it has seen the cancel."""
    events = list((await h.client.get_workflow_handle(WORKFLOW_ID).fetch_history()).events)
    requested = [i for i, e in enumerate(events) if e.HasField("workflow_execution_cancel_requested_event_attributes")]
    return bool(requested) and any(
        event.HasField("workflow_task_completed_event_attributes") for event in events[requested[0] :]
    )


async def _cancel_while_recording_the_first_failure(h: Harness, reply: dict, *, succeeded: bool = False) -> None:
    """End run 1's first attempt, and cancel the workflow inside its record, holding it until the cancel is seen.

    The record replies ``reply``. The workflow is waited for until it ends cancelled.
    """
    h.fakes.callbacks = {(COMPACTION, 1): [(1, succeeded, None if succeeded else "boom")]}
    h.fakes.record_replies = {(COMPACTION, 1): reply}

    async def hook(request: dict) -> None:
        if (request["operation"], request["attempt"]) == (COMPACTION, 1):
            await h.client.get_workflow_handle(WORKFLOW_ID).cancel()
            await eventually(lambda: _cancel_reached_the_workflow(h), bool, timeout=REAL_TIMEOUT_SECONDS)

    h.fakes.record_hook = hook
    handle = await h.start_maintenance(COMPACTION, EXPIRE)
    with pytest.raises(WorkflowFailureError) as caught:
        await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)
    assert isinstance(caught.value.cause, CancelledError)


def test_a_cancel_while_a_retrying_failure_is_recorded_cancels_the_waiting_run():
    """A cancel during the record of a failure that retries lets the record end, then cancels the run it left waiting.

    The record is not cancelled, no retry is submitted, the run never reached is skipped and the parent is told.
    """

    async def scenario(h: Harness) -> None:
        await _cancel_while_recording_the_first_failure(
            h, {"status": "retry_waiting", "failure_class": "other", "next_step": "retry_same"}
        )

        assert [c["run_id"] for c in h.fakes.cancels] == [RUN_IDS[0]]
        assert not await _cancel_requested_for_an_activity(h)
        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [(COMPACTION, 1)]
        assert [s["run_id"] for s in h.fakes.skips] == [RUN_IDS[1]]
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:2]))]

    _run(scenario)


def test_a_cancel_while_a_failure_that_does_not_retry_is_recorded_cancels_no_run():
    """A cancel during the record of a failure that ends the run lets the record end; no run is cancelled on top."""

    async def scenario(h: Harness) -> None:
        await _cancel_while_recording_the_first_failure(
            h, {"status": "failed", "failure_class": "other", "next_step": "not_retried"}
        )

        assert h.fakes.cancels == []
        assert not await _cancel_requested_for_an_activity(h)
        assert [(s["operation"], s["attempt"]) for s in h.fakes.submits] == [(COMPACTION, 1)]
        assert [s["run_id"] for s in h.fakes.skips] == [RUN_IDS[1]]
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:2]))]

    _run(scenario)


def test_a_cancel_while_a_success_is_recorded_cancels_no_run():
    """A cancel during the record of a success ends the workflow without cancelling the run."""

    async def scenario(h: Harness) -> None:
        await _cancel_while_recording_the_first_failure(h, {"status": "succeeded"}, succeeded=True)

        assert h.fakes.cancels == []
        assert [s["run_id"] for s in h.fakes.skips] == [RUN_IDS[1]]
        assert await h.parent_payloads() == [_report(run_ids=list(RUN_IDS[:2]))]

    _run(scenario)


def test_a_cancel_during_an_attempt_cancels_no_run_by_itself():
    """A cancel that interrupts an attempt is recorded on that attempt; the run is not cancelled a second way."""

    async def scenario(h: Harness) -> None:
        cancelled: list[bool] = []
        _cancel_on_the_first_status_poll(h, cancelled)
        handle = await h.start_maintenance(COMPACTION)
        with pytest.raises(WorkflowFailureError):
            await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)
        assert cancelled == [True]
        assert h.recorded() == [(COMPACTION, 1, False, "cancelled")]
        assert h.fakes.cancels == []

    _run(scenario)


async def _oom_then_a_larger_size(h: Harness) -> WorkflowHandle:
    h.fakes.callbacks = {(COMPACTION, 1): [(1, False, OOM_ERROR)], (COMPACTION, 2): [(2, True, None)]}
    h.fakes.record_replies = {
        (COMPACTION, 1): {"failure_class": "oom", "next_step": "retry_larger", "next_size": "M"},
    }
    return await h.start_maintenance(COMPACTION)


async def _a_timed_out_attempt(h: Harness) -> WorkflowHandle:
    h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}
    return await h.start_maintenance(COMPACTION, attempt_deadline_seconds=FENCE_DEADLINE_SECONDS)


async def _a_missing_job(h: Harness) -> WorkflowHandle:
    h.fakes.states[FIRST] = {"state": "NOT_FOUND", "error": None}
    h.fakes.callbacks = {(COMPACTION, 2): [(2, True, None)]}
    return await h.start_maintenance(COMPACTION)


async def _two_runs_waiting_for_jobs_gone(h: Harness) -> WorkflowHandle:
    h.fakes.callbacks = {(COMPACTION, 1): [(1, True, None)], (EXPIRE, 1): [(1, True, None)]}
    h.fakes.vanish_after_delete[FIRST_APP] = JOB_STAYS
    h.fakes.pods_live_for[FIRST_APP] = PODS_STAY
    return await h.start_maintenance(COMPACTION, EXPIRE)


async def _a_cancel_during_an_attempt(h: Harness) -> WorkflowHandle:
    _cancel_on_the_first_status_poll(h, [])
    return await h.start_maintenance(COMPACTION, EXPIRE)


@pytest.mark.parametrize(
    "start",
    [
        _oom_then_a_larger_size,
        _a_timed_out_attempt,
        _a_missing_job,
        _two_runs_waiting_for_jobs_gone,
        _a_cancel_during_an_attempt,
    ],
    ids=["oom-retry-larger", "timed-out", "missing-job", "jobs-gone-between-runs", "cancelled"],
)
def test_current_histories_replay(start: Callable[[Harness], Awaitable[WorkflowHandle]]):
    """A history the current workflow writes replays on it without non-determinism.

    The worker keeps no workflow in its cache, so every workflow task already replays the history so far;
    the finished history is then replayed once more on its own.
    """

    async def scenario(h: Harness) -> None:
        handle = await start(h)
        with contextlib.suppress(WorkflowFailureError):
            await asyncio.wait_for(handle.result(), timeout=REAL_TIMEOUT_SECONDS)
        history = await handle.fetch_history()
        await Replayer(workflows=[TableMaintenanceWorkflow]).replay_workflow(history)

    _run(scenario, max_cached_workflows=0)
