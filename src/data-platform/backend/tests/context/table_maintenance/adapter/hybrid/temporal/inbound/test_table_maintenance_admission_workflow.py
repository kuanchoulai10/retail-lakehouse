"""Test the TableMaintenanceAdmissionWorkflow on a time-skipping Temporal test server."""

from __future__ import annotations

import asyncio
import uuid
from datetime import timedelta
from typing import TYPE_CHECKING

from temporalio.common import WorkflowIDConflictPolicy
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance_admission import (
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW,
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID,
    AdmissionAcquireSignal,
    AdmissionReleaseSignal,
    AdmissionRenewSignal,
    TableMaintenanceAdmissionSignal,
    TableMaintenanceAdmissionWorkflowInput,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import (
    TableMaintenanceAdmissionWorkflow,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.eventually import (
    eventually,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.requester_stub_workflow import (
    RequesterStubWorkflow,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from temporalio.client import Client, WorkflowHandle


class AdmissionHarness:
    """Run the admission workflow with requester stubs and send it acquire and release signals."""

    def __init__(self, env: WorkflowEnvironment, queue: str, limit: int, lease: int):
        """Hold the environment and the queue, limit and lease the workflow runs with."""
        self.env = env
        self.client: Client = env.client
        self.queue = queue
        self.limit = limit
        self.lease = lease
        self.requesters: dict[str, WorkflowHandle] = {}

    async def requester(self, name: str) -> str:
        """Start a requester stub workflow and return its workflow id."""
        handle = await self.client.start_workflow("RequesterStub", id=f"req-{name}", task_queue=f"{self.queue}-stub")
        self.requesters[name] = handle
        return handle.id

    async def acquire(self, request_id: str, requester_workflow_id: str, lease_seconds: int | None = None) -> None:
        """Signal the admission workflow to acquire a slot for a request, with its own lease when given."""
        await self.client.start_workflow(
            TABLE_MAINTENANCE_ADMISSION_WORKFLOW,
            TableMaintenanceAdmissionWorkflowInput(limit=self.limit, lease_seconds=self.lease),
            id=TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID,
            task_queue=self.queue,
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
            start_signal=TableMaintenanceAdmissionSignal.ACQUIRE,
            start_signal_args=[AdmissionAcquireSignal(request_id, requester_workflow_id, lease_seconds)],
        )

    async def release(self, request_id: str) -> None:
        """Signal the admission workflow to release the slot of a request."""
        handle = self.client.get_workflow_handle(TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID)
        await handle.signal(TableMaintenanceAdmissionSignal.RELEASE, AdmissionReleaseSignal(request_id))

    async def renew(self, request_id: str) -> None:
        """Signal the admission workflow to restart the lease of a request."""
        handle = self.client.get_workflow_handle(TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID)
        await handle.signal(TableMaintenanceAdmissionSignal.RENEW, AdmissionRenewSignal(request_id))

    async def granted(self, name: str) -> list[str]:
        """Return the request ids granted to a requester."""
        return await self.requesters[name].query("granted")

    async def state(self) -> dict:
        """Query the admission workflow for its holders and queue."""
        return await self.client.get_workflow_handle(TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID).query("state")


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
    """At most the limit of requests hold a slot and the rest wait in the queue."""

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
    """Queued requests are granted in the order they arrived."""

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
    """A holder that never releases loses its slot when the lease expires and the next request gets it."""

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
    """A repeated acquire changes nothing and resends the grant when the request already holds a slot."""

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
    """A requester that no longer exists does not block the slots of the others."""

    async def scenario(h: AdmissionHarness) -> None:
        b = await h.requester("b")
        await h.acquire("r-ghost", "no-such-workflow")
        await h.acquire("r-b", b)
        await eventually(lambda: h.granted("b"), lambda g: g == ["r-b"])
        assert list((await h.state())["holders"]) == ["r-b"]

    _run(scenario, limit=1)


def test_release_of_unknown_or_queued_request():
    """Releasing an unknown or queued request removes it without granting anything wrongly."""

    async def scenario(h: AdmissionHarness) -> None:
        ids = {name: await h.requester(name) for name in ("a", "b", "c")}
        for name in ("a", "b", "c"):
            await h.acquire(f"r-{name}", ids[name])
        await h.release("unknown")
        await h.release("r-b")
        await eventually(
            h.state,
            lambda s: not any(e["request_id"] == "r-b" for e in s["queue"]),
        )
        await h.release("r-a")
        await eventually(lambda: h.granted("c"), lambda g: g == ["r-c"])
        assert await h.granted("b") == []

    _run(scenario, limit=1)


def test_renew_restarts_the_lease_of_a_holder():
    """A renewed holder keeps its slot past the lease it was granted with, until a full lease after the renew."""

    async def scenario(h: AdmissionHarness) -> None:
        a, b = await h.requester("a"), await h.requester("b")
        await h.acquire("r-a", a)
        await eventually(lambda: h.granted("a"), lambda g: g == ["r-a"])
        await h.acquire("r-b", b)
        await h.env.sleep(timedelta(seconds=h.lease - 60))
        before = (await h.state())["holders"]["r-a"]["granted_at"]
        await h.renew("r-a")
        await eventually(h.state, lambda s: s["holders"]["r-a"]["granted_at"] != before)
        await h.env.sleep(timedelta(seconds=120))
        state = await h.state()
        assert list(state["holders"]) == ["r-a"]
        assert await h.granted("b") == []

        await h.env.sleep(timedelta(seconds=h.lease))
        await eventually(lambda: h.granted("b"), lambda g: g == ["r-b"])

    _run(scenario, limit=1, lease=600)


def test_holder_keeps_the_lease_its_acquire_asked_for():
    """A request that brings its own lease keeps its slot for that lease, not the one the workflow started with."""

    async def scenario(h: AdmissionHarness) -> None:
        a, b = await h.requester("a"), await h.requester("b")
        await h.acquire("r-a", a, lease_seconds=3600)
        await eventually(lambda: h.granted("a"), lambda g: g == ["r-a"])
        await h.acquire("r-b", b)
        await h.env.sleep(timedelta(seconds=1200))
        assert list((await h.state())["holders"]) == ["r-a"]
        assert await h.granted("b") == []

        await h.env.sleep(timedelta(seconds=2500))
        await eventually(lambda: h.granted("b"), lambda g: g == ["r-b"])

    _run(scenario, limit=1, lease=600)


def test_renew_of_an_unknown_request_is_ignored():
    """Renewing a request that holds no slot neither grants nor queues it."""

    async def scenario(h: AdmissionHarness) -> None:
        a = await h.requester("a")
        await h.acquire("r-a", a)
        await eventually(lambda: h.granted("a"), lambda g: g == ["r-a"])
        before = await h.state()
        await h.renew("unknown")
        await h.release("r-none")
        state = await eventually(h.state, lambda s: s == before)
        assert list(state["holders"]) == ["r-a"]
        assert state["queue"] == []

    _run(scenario, limit=1)
