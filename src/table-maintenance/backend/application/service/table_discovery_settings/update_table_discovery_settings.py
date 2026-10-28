"""Define the UpdateTableDiscoverySettingsService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.port.inbound.table_discovery_settings.update_table_discovery_settings import (
    UpdateTableDiscoverySettingsUseCase,
    UpdateTableDiscoverySettingsUseCaseInput,
    UpdateTableDiscoverySettingsUseCaseOutput,
)
from application.port.outbound.table_discovery_settings.update_table_discovery_schedule import (
    UpdateTableDiscoveryScheduleGatewayInput,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from application.port.outbound.table_discovery_settings.table_discovery_settings_repo import (
        TableDiscoverySettingsRepo,
    )
    from application.port.outbound.table_discovery_settings.update_table_discovery_schedule import (
        UpdateTableDiscoveryScheduleGateway,
    )


class UpdateTableDiscoverySettingsService(UpdateTableDiscoverySettingsUseCase):
    """Turn discovery on or off and pause or unpause its schedule."""

    def __init__(
        self,
        settings_repo: TableDiscoverySettingsRepo,
        schedule_gateway: UpdateTableDiscoveryScheduleGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repo, the schedule gateway and the clock."""
        self._settings_repo = settings_repo
        self._schedule_gateway = schedule_gateway
        self._clock = clock

    def execute(
        self, request: UpdateTableDiscoverySettingsUseCaseInput
    ) -> UpdateTableDiscoverySettingsUseCaseOutput:
        """Save the switch, then update the schedule to match."""
        settings = self._settings_repo.get_settings()
        if request.enabled:
            settings.enable(self._clock())
        else:
            settings.disable(self._clock())
        self._settings_repo.save(settings)
        self._schedule_gateway.update(
            UpdateTableDiscoveryScheduleGatewayInput(paused=not settings.enabled)
        )
        return UpdateTableDiscoverySettingsUseCaseOutput(
            enabled=settings.enabled, updated_at=settings.updated_at
        )
