"""Test the TableMaintenanceAdmissionWorkflow on a time-skipping Temporal test server."""

from __future__ import annotations

import asyncio
import uuid
from datetime import timedelta
from typing import TYPE_CHECKING

from temporalio.common import WorkflowIDConflictPolicy
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from adapter.inbound.temporal.workflows import TableMaintenanceAdmissionWorkflow
from adapter.temporal_contracts.admission_acquire_signal import AdmissionAcquireSignal
from adapter.temporal_contracts.table_maintenance_admission_input import (
    TableMaintenanceAdmissionInput,
)
from adapter.temporal_contracts.admission_release_signal import AdmissionReleaseSignal
from adapter.temporal_contracts.workflow_names import (
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW,
)
from application.domain.model.maintenance.workflow_ids import (
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID,
    SIGNAL_ADMISSION_ACQUIRE,
    SIGNAL_ADMISSION_RELEASE,
)
from tests.adapter.inbound.temporal.eventually import eventually
from tests.adapter.inbound.temporal.requester_stub_workflow import (
    RequesterStubWorkflow,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from temporalio.client import Client, WorkflowHandle


class AdmissionHarness:
    def __init__(self, env: WorkflowEnvironment, queue: str, limit: int, lease: int):
        self.env = env
        self.client: Client = env.client
        self.queue = queue
        self.limit = limit
        self.lease = lease
        self.requesters: dict[str, WorkflowHandle] = {}

    async def requester(self, name: str) -> str:
        handle = await self.client.start_workflow(
            "RequesterStub", id=f"req-{name}", task_queue=f"{self.queue}-stub"
        )
        self.requesters[name] = handle
        return handle.id

    async def acquire(self, request_id: str, requester_workflow_id: str) -> None:
        await self.client.start_workflow(
            TABLE_MAINTENANCE_ADMISSION_WORKFLOW,
            TableMaintenanceAdmissionInput(limit=self.limit, lease_seconds=self.lease),
            id=TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID,
            task_queue=self.queue,
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
            start_signal=SIGNAL_ADMISSION_ACQUIRE,
            start_signal_args=[
                AdmissionAcquireSignal(request_id, requester_workflow_id)
            ],
        )

    async def release(self, request_id: str) -> None:
        handle = self.client.get_workflow_handle(
            TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID
        )
        await handle.signal(
            SIGNAL_ADMISSION_RELEASE, AdmissionReleaseSignal(request_id)
        )

    async def granted(self, name: str) -> list[str]:
        return await self.requesters[name].query("granted")

    async def state(self) -> dict:
        return await self.client.get_workflow_handle(
            TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID
        ).query("state")


def _run(
    scenario: Callable[[AdmissionHarness], Awaitable[None]],
    limit: int = 2,
    lease: int = 21600,
) -> None:
    async def go() -> None:
        async with await WorkflowEnvironment.start_time_skipping() as env:
            queue = f"q-{uuid.uuid4()}"
            async with (
                Worker(
                    env.client,
                    task_queue=queue,
                    workflows=[TableMaintenanceAdmissionWorkflow],
                ),
                Worker(
                    env.client,
                    task_queue=f"{queue}-stub",
                    workflows=[RequesterStubWorkflow],
                    workflow_runner=UnsandboxedWorkflowRunner(),
                ),
            ):
                await scenario(AdmissionHarness(env, queue, limit, lease))

    asyncio.run(go())


def test_admission_never_exceeds_limit():
    async def scenario(h: AdmissionHarness) -> None:
        ids = {name: await h.requester(name) for name in ("a", "b", "c")}
        for name in ("a", "b", "c"):
            await h.acquire(f"r-{name}", ids[name])
        await eventually(lambda: h.granted("b"), lambda g: g == ["r-b"])
        assert await h.granted("a") == ["r-a"]
        state = await h.state()
        assert sorted(state["holders"]) == ["r-a", "r-b"]
        assert [e["request_id"] for e in state["queue"]] == ["r-c"]
        await h.env.sleep(timedelta(hours=1))
        assert await h.granted("c") == []

        await h.release("r-a")
        await eventually(lambda: h.granted("c"), lambda g: g == ["r-c"])
        assert sorted((await h.state())["holders"]) == ["r-b", "r-c"]

    _run(scenario, limit=2)


def test_admission_grants_in_fifo_order():
    async def scenario(h: AdmissionHarness) -> None:
        ids = {name: await h.requester(name) for name in ("a", "b", "c")}
        for name in ("a", "b", "c"):
            await h.acquire(f"r-{name}", ids[name])
        await eventually(lambda: h.granted("a"), lambda g: g == ["r-a"])
        await h.release("r-a")
        await eventually(lambda: h.granted("b"), lambda g: g == ["r-b"])
        assert await h.granted("c") == []

    _run(scenario, limit=1)


def test_admission_lease_expires_when_holder_never_releases():
    async def scenario(h: AdmissionHarness) -> None:
        a, b = await h.requester("a"), await h.requester("b")
        await h.acquire("r-a", a)
        await eventually(lambda: h.granted("a"), lambda g: g == ["r-a"])
        await h.acquire("r-b", b)
        await h.env.sleep(timedelta(seconds=h.lease - 10))
        assert await h.granted("b") == []

        await h.env.sleep(timedelta(seconds=11))
        await eventually(lambda: h.granted("b"), lambda g: g == ["r-b"])
        assert list((await h.state())["holders"]) == ["r-b"]

    _run(scenario, limit=1, lease=600)


def test_duplicate_acquire_is_a_no_op_and_resends_grant_when_held():
    async def scenario(h: AdmissionHarness) -> None:
        a, b = await h.requester("a"), await h.requester("b")
        await h.acquire("r-a", a)
        await h.acquire("r-a", a)
        await h.acquire("r-b", b)
        await h.acquire("r-b", b)
        await eventually(lambda: h.granted("a"), lambda g: g == ["r-a", "r-a"])
        state = await h.state()
        assert list(state["holders"]) == ["r-a"]
        assert [e["request_id"] for e in state["queue"]] == ["r-b"]

    _run(scenario, limit=1)


def test_vanished_requester_does_not_wedge_the_admission_workflow():
    async def scenario(h: AdmissionHarness) -> None:
        b = await h.requester("b")
        await h.acquire("r-ghost", "no-such-workflow")
        await h.acquire("r-b", b)
        await eventually(lambda: h.granted("b"), lambda g: g == ["r-b"])
        assert list((await h.state())["holders"]) == ["r-b"]

    _run(scenario, limit=1)


def test_release_of_unknown_or_queued_request():
    async def scenario(h: AdmissionHarness) -> None:
        ids = {name: await h.requester(name) for name in ("a", "b", "c")}
        for name in ("a", "b", "c"):
            await h.acquire(f"r-{name}", ids[name])
        await h.release("unknown")
        await h.release("r-b")
        await eventually(
            lambda: h.state(),
            lambda s: not any(e["request_id"] == "r-b" for e in s["queue"]),
        )
        await h.release("r-a")
        await eventually(lambda: h.granted("c"), lambda g: g == ["r-c"])
        assert await h.granted("b") == []

    _run(scenario, limit=1)
