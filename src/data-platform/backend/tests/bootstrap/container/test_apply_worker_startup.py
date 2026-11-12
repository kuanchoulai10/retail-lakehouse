"""Test the worker startup step that ensures the Temporal schedules and admission workflow."""

from __future__ import annotations

import asyncio
import inspect
from datetime import timedelta
from typing import TYPE_CHECKING, Any, cast

from bootstrap.configs import CatalogSettings
from bootstrap.container import apply_worker_startup
from context.table_maintenance.adapter.hybrid.temporal.inbound import (
    ensure_table_discovery_schedule,
    ensure_table_maintenance_admission,
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


def _run() -> tuple[Recorder, Recorder, object]:
    schedule, admission, client = Recorder(), Recorder(), object()
    settings = sqlite_settings(
        catalog=CatalogSettings(names=["a", "b"]),
        admission_limit=3,
        discovery_interval_seconds=120,
        maintenance_attempt_deadline_seconds=600,
    )
    asyncio.run(
        apply_worker_startup(
            cast("Client", client),
            settings,
            ensure_schedule=schedule,
            ensure_admission=admission,
        )
    )
    return schedule, admission, client


def test_worker_startup_never_pauses_schedule():
    """The discovery schedules are ensured for every covered catalog with no paused flag: they always run."""
    schedule, _, client = _run()

    assert schedule.calls == [((client, ["a", "b"]), {"interval": timedelta(seconds=120)})]
    assert "paused" not in inspect.signature(ensure_table_discovery_schedule).parameters


def test_admission_is_ensured_with_the_configured_limit():
    """The admission workflow is ensured with the configured limit and a lease 15 minutes past the deadline."""
    _, admission, client = _run()

    assert admission.calls == [
        (
            (client,),
            {
                "limit": 3,
                "lease_seconds": 1500,
            },
        )
    ]


def test_defaults_are_the_real_functions_and_the_kwargs_bind_to_them():
    """The default ensure functions are the real ones and the keyword arguments bind to their signatures."""
    parameters = inspect.signature(apply_worker_startup).parameters
    assert parameters["ensure_schedule"].default is ensure_table_discovery_schedule
    assert parameters["ensure_admission"].default is ensure_table_maintenance_admission

    schedule, admission, _ = _run()

    for real, recorder in (
        (ensure_table_discovery_schedule, schedule),
        (ensure_table_maintenance_admission, admission),
    ):
        ((args, kwargs),) = recorder.calls
        inspect.signature(real).bind(*args, **kwargs)
