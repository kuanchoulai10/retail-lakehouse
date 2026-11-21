"""Test the worker startup step that checks the search attributes and syncs the discovery schedules."""

from __future__ import annotations

import asyncio
import inspect
import threading
from typing import TYPE_CHECKING, Any, cast

import pytest

from bootstrap.container import apply_worker_startup
from context.table_maintenance.adapter.hybrid.temporal.inbound import (
    MissingTableSearchAttributes,
    require_table_search_attributes,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy_attachment import (
    SyncDiscoverySchedulesUseCase,
    SyncDiscoverySchedulesUseCaseInput,
    SyncDiscoverySchedulesUseCaseOutput,
)

if TYPE_CHECKING:
    from temporalio.client import Client

    from bootstrap.container import UseCases


class _RecordingSync(SyncDiscoverySchedulesUseCase):
    """Record each sync and the thread it ran on, appending to a shared log of startup steps."""

    def __init__(self, steps: list[str], *, error: Exception | None = None) -> None:
        self.steps = steps
        self.error = error
        self.requests: list[SyncDiscoverySchedulesUseCaseInput] = []
        self.threads: list[int] = []

    def execute(self, request: SyncDiscoverySchedulesUseCaseInput) -> SyncDiscoverySchedulesUseCaseOutput:
        self.steps.append("sync")
        self.requests.append(request)
        self.threads.append(threading.get_ident())
        if self.error is not None:
            raise self.error
        return SyncDiscoverySchedulesUseCaseOutput(catalogs=("iceberg",))


class _UseCases:
    def __init__(self, sync: _RecordingSync) -> None:
        self.sync_discovery_schedules = sync


def _start(sync: _RecordingSync, require: Any = None) -> int:  # noqa: ANN401
    """Run the startup and return the id of the thread its event loop ran on."""
    steps = sync.steps

    async def check(_client: object) -> None:
        steps.append("check")

    async def run() -> int:
        await apply_worker_startup(
            cast("Client", object()),
            cast("UseCases", _UseCases(sync)),
            require_attributes=check if require is None else require,
        )
        return threading.get_ident()

    return asyncio.run(run())


def test_worker_startup_syncs_the_discovery_schedules():
    """After the search-attribute check, the schedules are synced once, off the event loop's thread."""
    sync = _RecordingSync([])

    loop_thread = _start(sync)

    assert sync.steps == ["check", "sync"]
    assert sync.requests == [SyncDiscoverySchedulesUseCaseInput()]
    assert sync.threads != [loop_thread]


def test_worker_startup_fails_when_the_sync_fails():
    """A sync that fails stops the start, loudly."""
    sync = _RecordingSync([], error=RuntimeError("temporal is down"))

    with pytest.raises(RuntimeError, match="temporal is down"):
        _start(sync)


def test_missing_search_attributes_stop_the_start_before_any_sync():
    """A namespace without the attributes fails the start, and no schedule is synced."""
    sync = _RecordingSync([])

    async def missing(_client: object) -> None:
        raise MissingTableSearchAttributes("run platform/21-temporal/bootstrap.sh")

    with pytest.raises(MissingTableSearchAttributes):
        _start(sync, require=missing)
    assert sync.requests == []


def test_the_default_check_is_the_real_one():
    """The default search-attribute check is the real one and takes the client."""
    parameters = inspect.signature(apply_worker_startup).parameters

    assert parameters["require_attributes"].default is require_table_search_attributes
    inspect.signature(require_table_search_attributes).bind(object())


def test_no_admission_workflow_or_other_schedule_is_ensured():
    """The worker ensures no admission workflow and no round schedule: its startup takes no ensure step."""
    parameters = inspect.signature(apply_worker_startup).parameters

    assert [name for name in parameters if name.startswith("ensure_")] == []
