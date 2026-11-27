"""Test the worker startup step that checks the search attributes and ensures the discovery schedule."""

from __future__ import annotations

import asyncio
import inspect
from datetime import timedelta
from typing import TYPE_CHECKING, Any, cast

import pytest
from temporalio.client import Schedule, ScheduleActionStartWorkflow

from bootstrap.container import apply_worker_startup
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_SCHEDULE_ID,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery_round import (
    TABLE_DISCOVERY_ROUND_WORKFLOW,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound import (
    MissingTableSearchAttributes,
    require_table_search_attributes,
)

if TYPE_CHECKING:
    from temporalio.client import Client

    from bootstrap.container import UseCases


class _RecordingClient:
    """Record each schedule created, appending to a shared log of startup steps."""

    def __init__(self, steps: list[str], *, error: Exception | None = None) -> None:
        self.steps = steps
        self.error = error
        self.created: list[tuple[str, Schedule]] = []

    async def create_schedule(self, schedule_id: str, schedule: Schedule, **_: Any) -> None:  # noqa: ANN401
        self.steps.append("schedule")
        if self.error is not None:
            raise self.error
        self.created.append((schedule_id, schedule))


def _start(client: _RecordingClient, *, interval: timedelta = timedelta(seconds=600), require: Any = None) -> None:  # noqa: ANN401
    steps = client.steps

    async def check(_client: object) -> None:
        steps.append("check")

    asyncio.run(
        apply_worker_startup(
            cast("Client", client),
            cast("UseCases", object()),
            interval=interval,
            require_attributes=check if require is None else require,
        )
    )


def test_worker_startup_ensures_the_discovery_schedule_at_the_interval():
    """After the search-attribute check, the one discovery schedule is ensured at the interval given."""
    client = _RecordingClient([])

    _start(client, interval=timedelta(seconds=42))

    assert client.steps == ["check", "schedule"]
    ((schedule_id, schedule),) = client.created
    assert schedule_id == TABLE_DISCOVERY_SCHEDULE_ID
    assert [spec.every for spec in schedule.spec.intervals] == [timedelta(seconds=42)]
    assert isinstance(schedule.action, ScheduleActionStartWorkflow)
    assert schedule.action.workflow == TABLE_DISCOVERY_ROUND_WORKFLOW


def test_worker_startup_fails_when_the_schedule_cannot_be_ensured():
    """A schedule that cannot be ensured stops the start, loudly."""
    client = _RecordingClient([], error=RuntimeError("temporal is down"))

    with pytest.raises(RuntimeError, match="temporal is down"):
        _start(client)


def test_missing_search_attributes_stop_the_start_before_the_schedule():
    """A namespace without the attributes fails the start, and no schedule is ensured."""
    client = _RecordingClient([])

    async def missing(_client: object) -> None:
        raise MissingTableSearchAttributes("run platform/21-temporal/bootstrap.sh")

    with pytest.raises(MissingTableSearchAttributes):
        _start(client, require=missing)
    assert client.steps == []


def test_the_default_check_is_the_real_one():
    """The default search-attribute check is the real one and takes the client."""
    parameters = inspect.signature(apply_worker_startup).parameters

    assert parameters["require_attributes"].default is require_table_search_attributes
    inspect.signature(require_table_search_attributes).bind(object())


def test_the_interval_has_no_default():
    """The interval always comes from the worker's settings, so the startup takes it with no default."""
    parameters = inspect.signature(apply_worker_startup).parameters

    assert parameters["interval"].default is inspect.Parameter.empty
    assert parameters["interval"].kind is inspect.Parameter.KEYWORD_ONLY
