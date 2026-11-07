"""Test the discovery switch use case services."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.table_discovery_settings import (
    GetTableDiscoverySettingsUseCaseInput,
    UpdateTableDiscoverySettingsUseCaseInput,
)
from context.table_maintenance.application.port.outbound.table_discovery_settings import (
    UpdateTableDiscoveryScheduleGateway,
)
from context.table_maintenance.application.service.table_discovery_settings import (
    GetTableDiscoverySettingsService,
    UpdateTableDiscoverySettingsService,
)


def test_get_settings_defaults_to_enabled(table_discovery_settings_repo):
    """Without stored settings, discovery reads as enabled."""
    out = GetTableDiscoverySettingsService(table_discovery_settings_repo).execute(
        GetTableDiscoverySettingsUseCaseInput()
    )
    assert out.enabled is True


def test_disabling_discovery_pauses_schedule(table_discovery_settings_repo, schedule, clock):
    """Disabling discovery stores the flag and pauses the schedule."""
    service = UpdateTableDiscoverySettingsService(table_discovery_settings_repo, schedule, clock=clock)
    out = service.execute(UpdateTableDiscoverySettingsUseCaseInput(enabled=False))
    assert out.enabled is False
    assert table_discovery_settings_repo.get_settings().enabled is False
    assert [c.paused for c in schedule.calls] == [True]


def test_enabling_discovery_unpauses_schedule(table_discovery_settings_repo, schedule, clock):
    """Enabling discovery unpauses the schedule."""
    service = UpdateTableDiscoverySettingsService(table_discovery_settings_repo, schedule, clock=clock)
    service.execute(UpdateTableDiscoverySettingsUseCaseInput(enabled=False))
    out = service.execute(UpdateTableDiscoverySettingsUseCaseInput(enabled=True))
    assert out.enabled is True
    assert [c.paused for c in schedule.calls] == [True, False]


def test_settings_are_saved_before_schedule_is_updated(table_discovery_settings_repo, clock):
    """The settings are saved before the schedule is updated."""
    seen: list[bool] = []

    class _Schedule(UpdateTableDiscoveryScheduleGateway):
        def update(self, input):  # noqa: A002
            seen.append(table_discovery_settings_repo.get_settings().enabled)

    UpdateTableDiscoverySettingsService(table_discovery_settings_repo, _Schedule(), clock=clock).execute(
        UpdateTableDiscoverySettingsUseCaseInput(enabled=False)
    )
    assert seen == [False]
