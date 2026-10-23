from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any, cast

from temporalio.client import Client

from adapter.outbound.discovery.sql.discovery_settings_sql_repo import (
    DiscoverySettingsSqlRepo,
)
from application.domain.model.discovery.discovery_settings import DiscoverySettings
from application.service.discovery.get_discovery_settings import (
    GetDiscoverySettingsService,
)
from bootstrap.configs import CatalogSettings, TemporalSettings
from bootstrap.container import CAPACITY_LEASE_SECONDS, apply_worker_startup
from tests.bootstrap.container.container_support import (
    NOW,
    sqlite_engine,
    sqlite_settings,
)


class Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    async def __call__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        self.calls.append((args, kwargs))


def _run(repo: DiscoverySettingsSqlRepo) -> tuple[Recorder, Recorder, object]:
    schedule, limiter, client = Recorder(), Recorder(), object()
    settings = sqlite_settings(
        catalog=CatalogSettings(names=["a", "b"]),
        temporal=TemporalSettings(task_queue="q"),
        capacity_limit=3,
        discovery_interval_seconds=120,
    )
    asyncio.run(
        apply_worker_startup(
            cast("Client", client),
            settings,
            GetDiscoverySettingsService(repo),
            ensure_schedule=schedule,
            ensure_limiter=limiter,
        )
    )
    return schedule, limiter, client


def test_absent_discovery_row_means_enabled_schedules_unpaused():
    schedule, _, client = _run(DiscoverySettingsSqlRepo(sqlite_engine()))

    assert schedule.calls == [
        (
            (client, ["a", "b"]),
            {"paused": False, "interval": timedelta(seconds=120)},
        )
    ]


def test_disabled_discovery_pauses_the_schedules():
    repo = DiscoverySettingsSqlRepo(sqlite_engine())
    repo.save(DiscoverySettings.create(NOW, enabled=False))

    schedule, _, _ = _run(repo)

    assert schedule.calls[0][1]["paused"] is True


def test_capacity_limiter_is_ensured_with_the_configured_limit():
    _, limiter, client = _run(DiscoverySettingsSqlRepo(sqlite_engine()))

    assert limiter.calls == [
        (
            (client,),
            {
                "limit": 3,
                "lease_seconds": CAPACITY_LEASE_SECONDS,
                "task_queue": "q",
            },
        )
    ]
