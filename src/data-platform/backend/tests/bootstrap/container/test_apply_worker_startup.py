"""Test the worker startup step that ensures the Temporal schedules and admission workflow."""

from __future__ import annotations

import asyncio
import inspect
from datetime import timedelta
from typing import TYPE_CHECKING, Any, cast

from bootstrap.configs import CatalogSettings
from bootstrap.container import ADMISSION_LEASE_SECONDS, apply_worker_startup
from context.table_maintenance.adapter.hybrid.temporal.inbound import (
    ensure_table_discovery_schedule,
    ensure_table_maintenance_admission,
)
from context.table_maintenance.adapter.outbound.table_discovery_settings.sql import (
    TableDiscoverySettingsSqlRepo,
)
from context.table_maintenance.application.domain.model.table_discovery_settings import (
    TableDiscoverySettings,
)
from context.table_maintenance.application.service.table_discovery_settings import (
    GetTableDiscoverySettingsService,
)
from tests.bootstrap.container.container_support import (
    NOW,
    sqlite_engine,
    sqlite_settings,
)

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


def _run(repo: TableDiscoverySettingsSqlRepo) -> tuple[Recorder, Recorder, object]:
    schedule, admission, client = Recorder(), Recorder(), object()
    settings = sqlite_settings(
        catalog=CatalogSettings(names=["a", "b"]),
        admission_limit=3,
        discovery_interval_seconds=120,
    )
    asyncio.run(
        apply_worker_startup(
            cast("Client", client),
            settings,
            GetTableDiscoverySettingsService(repo),
            ensure_schedule=schedule,
            ensure_admission=admission,
        )
    )
    return schedule, admission, client


def test_absent_discovery_row_means_enabled_schedules_unpaused():
    """Without a stored discovery setting the schedules are ensured unpaused."""
    schedule, _, client = _run(TableDiscoverySettingsSqlRepo(sqlite_engine()))

    assert schedule.calls == [
        (
            (client, ["a", "b"]),
            {"paused": False, "interval": timedelta(seconds=120)},
        )
    ]


def test_disabled_discovery_pauses_the_schedules():
    """A disabled discovery setting makes the schedules paused."""
    repo = TableDiscoverySettingsSqlRepo(sqlite_engine())
    repo.save(TableDiscoverySettings.create(NOW, enabled=False))

    schedule, _, _ = _run(repo)

    assert schedule.calls[0][1]["paused"] is True


def test_admission_is_ensured_with_the_configured_limit():
    """The admission workflow is ensured with the configured concurrency limit."""
    _, admission, client = _run(TableDiscoverySettingsSqlRepo(sqlite_engine()))

    assert admission.calls == [
        (
            (client,),
            {
                "limit": 3,
                "lease_seconds": ADMISSION_LEASE_SECONDS,
            },
        )
    ]


def test_defaults_are_the_real_functions_and_the_kwargs_bind_to_them():
    """The default ensure functions are the real ones and the keyword arguments bind to their signatures."""
    parameters = inspect.signature(apply_worker_startup).parameters
    assert parameters["ensure_schedule"].default is ensure_table_discovery_schedule
    assert parameters["ensure_admission"].default is ensure_table_maintenance_admission

    schedule, admission, _ = _run(TableDiscoverySettingsSqlRepo(sqlite_engine()))

    for real, recorder in (
        (ensure_table_discovery_schedule, schedule),
        (ensure_table_maintenance_admission, admission),
    ):
        ((args, kwargs),) = recorder.calls
        inspect.signature(real).bind(*args, **kwargs)
