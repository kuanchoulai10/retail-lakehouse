"""Test the worker startup step that ensures the Temporal schedules."""

from __future__ import annotations

import asyncio
import inspect
from datetime import timedelta
from typing import TYPE_CHECKING, Any, cast

import pytest

from bootstrap.configs import CatalogSettings
from bootstrap.container import apply_worker_startup
from context.table_maintenance.adapter.hybrid.temporal.inbound import (
    MissingTableSearchAttributes,
    ensure_table_discovery_schedule,
    require_table_search_attributes,
)
from tests.bootstrap.container.container_support import sqlite_settings

if TYPE_CHECKING:
    from temporalio.client import Client


class Recorder:
    """Callable that records every call made to it."""

    def __init__(self) -> None:
        """Start with no recorded calls."""
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    async def __call__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Record the positional and keyword arguments of the call."""
        self.calls.append((args, kwargs))


def _run(require: Recorder | None = None) -> tuple[Recorder, object]:
    schedule, client = Recorder(), object()
    settings = sqlite_settings(
        catalog=CatalogSettings(names=["a", "b"]),
        discovery_interval_seconds=120,
        maintenance_attempt_deadline_seconds=600,
    )
    asyncio.run(
        apply_worker_startup(
            cast("Client", client),
            settings,
            ensure_schedule=schedule,
            require_attributes=Recorder() if require is None else require,
        )
    )
    return schedule, client


def test_worker_startup_never_pauses_schedule():
    """The discovery schedules are ensured for every covered catalog with no paused flag: they always run."""
    schedule, client = _run()

    assert schedule.calls == [((client, ["a", "b"]), {"interval": timedelta(seconds=120)})]
    assert "paused" not in inspect.signature(ensure_table_discovery_schedule).parameters


def test_no_admission_workflow_is_ensured():
    """The worker ensures no admission workflow: its startup takes no admission step."""
    assert "ensure_admission" not in inspect.signature(apply_worker_startup).parameters


def test_only_the_discovery_schedules_are_ensured():
    """The worker ensures the discovery schedules and no other: there is no round schedule any more."""
    parameters = inspect.signature(apply_worker_startup).parameters

    assert [name for name in parameters if name.startswith("ensure_")] == ["ensure_schedule"]


def test_defaults_are_the_real_functions_and_the_kwargs_bind_to_them():
    """The default ensure functions are the real ones and the keyword arguments bind to their signatures."""
    parameters = inspect.signature(apply_worker_startup).parameters
    assert parameters["ensure_schedule"].default is ensure_table_discovery_schedule
    assert parameters["require_attributes"].default is require_table_search_attributes

    schedule, _ = _run()

    ((args, kwargs),) = schedule.calls
    inspect.signature(ensure_table_discovery_schedule).bind(*args, **kwargs)


def test_the_search_attributes_are_checked_first():
    """The worker checks the namespace's search attributes before it ensures any schedule."""
    require = Recorder()
    _, client = _run(require)

    assert require.calls == [((client,), {})]
    inspect.signature(require_table_search_attributes).bind(client)


def test_missing_search_attributes_stop_the_start_before_any_schedule():
    """A namespace without the attributes fails the start, and no schedule is created."""
    schedule = Recorder()

    async def missing(_client: object) -> None:
        raise MissingTableSearchAttributes("run platform/21-temporal/bootstrap.sh")

    with pytest.raises(MissingTableSearchAttributes):
        asyncio.run(
            apply_worker_startup(
                cast("Client", object()),
                sqlite_settings(),
                ensure_schedule=schedule,
                require_attributes=missing,
            )
        )
    assert schedule.calls == []
