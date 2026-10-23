"""Test the discovery switch use case services."""

from __future__ import annotations

from application.port.inbound.discovery.get_discovery_settings import (
    GetDiscoverySettingsUseCaseInput,
)
from application.port.inbound.discovery.update_discovery_settings import (
    UpdateDiscoverySettingsUseCaseInput,
)
from application.port.outbound.discovery.update_discovery_schedule import (
    UpdateDiscoveryScheduleGateway,
)
from application.service.discovery.get_discovery_settings import (
    GetDiscoverySettingsService,
)
from application.service.discovery.update_discovery_settings import (
    UpdateDiscoverySettingsService,
)


def test_get_settings_defaults_to_enabled(discovery_settings_repo):
    out = GetDiscoverySettingsService(discovery_settings_repo).execute(
        GetDiscoverySettingsUseCaseInput()
    )
    assert out.enabled is True


def test_disabling_discovery_pauses_schedule(discovery_settings_repo, schedule, clock):
    service = UpdateDiscoverySettingsService(
        discovery_settings_repo, schedule, clock=clock
    )
    out = service.execute(UpdateDiscoverySettingsUseCaseInput(enabled=False))
    assert out.enabled is False
    assert discovery_settings_repo.get_settings().enabled is False
    assert [c.paused for c in schedule.calls] == [True]


def test_enabling_discovery_unpauses_schedule(discovery_settings_repo, schedule, clock):
    service = UpdateDiscoverySettingsService(
        discovery_settings_repo, schedule, clock=clock
    )
    service.execute(UpdateDiscoverySettingsUseCaseInput(enabled=False))
    out = service.execute(UpdateDiscoverySettingsUseCaseInput(enabled=True))
    assert out.enabled is True
    assert [c.paused for c in schedule.calls] == [True, False]


def test_settings_are_saved_before_schedule_is_updated(discovery_settings_repo, clock):
    seen: list[bool] = []

    class _Schedule(UpdateDiscoveryScheduleGateway):
        def update(self, input):  # noqa: A002
            seen.append(discovery_settings_repo.get_settings().enabled)

    UpdateDiscoverySettingsService(
        discovery_settings_repo, _Schedule(), clock=clock
    ).execute(UpdateDiscoverySettingsUseCaseInput(enabled=False))
    assert seen == [False]
