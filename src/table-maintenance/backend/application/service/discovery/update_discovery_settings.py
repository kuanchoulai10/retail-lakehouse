"""Define the UpdateDiscoverySettingsService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.port.inbound.discovery.update_discovery_settings import (
    UpdateDiscoverySettingsUseCase,
    UpdateDiscoverySettingsUseCaseInput,
    UpdateDiscoverySettingsUseCaseOutput,
)
from application.port.outbound.discovery.update_discovery_schedule import (
    UpdateDiscoveryScheduleGatewayInput,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from application.port.outbound.discovery.discovery_settings_repo import (
        DiscoverySettingsRepo,
    )
    from application.port.outbound.discovery.update_discovery_schedule import (
        UpdateDiscoveryScheduleGateway,
    )


class UpdateDiscoverySettingsService(UpdateDiscoverySettingsUseCase):
    """Turn discovery on or off and pause or unpause its schedule."""

    def __init__(
        self,
        settings_repo: DiscoverySettingsRepo,
        schedule_gateway: UpdateDiscoveryScheduleGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repo, the schedule gateway and the clock."""
        self._settings_repo = settings_repo
        self._schedule_gateway = schedule_gateway
        self._clock = clock

    def execute(
        self, request: UpdateDiscoverySettingsUseCaseInput
    ) -> UpdateDiscoverySettingsUseCaseOutput:
        """Save the switch, then update the schedule to match."""
        settings = self._settings_repo.get_settings()
        if request.enabled:
            settings.enable(self._clock())
        else:
            settings.disable(self._clock())
        self._settings_repo.save(settings)
        self._schedule_gateway.update(
            UpdateDiscoveryScheduleGatewayInput(paused=not settings.enabled)
        )
        return UpdateDiscoverySettingsUseCaseOutput(
            enabled=settings.enabled, updated_at=settings.updated_at
        )
