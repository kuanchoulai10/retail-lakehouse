from __future__ import annotations

import asyncio
import inspect
from datetime import timedelta
from typing import Any, cast

from temporalio.client import Client

from adapter.inbound.temporal.ensure_table_maintenance_admission import (
    ensure_table_maintenance_admission,
)
from adapter.inbound.temporal.ensure_table_discovery_schedule import (
    ensure_table_discovery_schedule,
)
from adapter.outbound.table_discovery_settings.sql.table_discovery_settings_sql_repo import (
    TableDiscoverySettingsSqlRepo,
)
from application.domain.model.table_discovery_settings.table_discovery_settings import (
    TableDiscoverySettings,
)
from application.service.table_discovery_settings.get_table_discovery_settings import (
    GetTableDiscoverySettingsService,
)
from bootstrap.configs import CatalogSettings
from bootstrap.container import ADMISSION_LEASE_SECONDS, apply_worker_startup
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
    schedule, _, client = _run(TableDiscoverySettingsSqlRepo(sqlite_engine()))

    assert schedule.calls == [
        (
            (client, ["a", "b"]),
            {"paused": False, "interval": timedelta(seconds=120)},
        )
    ]


def test_disabled_discovery_pauses_the_schedules():
    repo = TableDiscoverySettingsSqlRepo(sqlite_engine())
    repo.save(TableDiscoverySettings.create(NOW, enabled=False))

    schedule, _, _ = _run(repo)

    assert schedule.calls[0][1]["paused"] is True


def test_admission_is_ensured_with_the_configured_limit():
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
