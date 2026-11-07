"""Define the GetTableDiscoverySettingsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.inbound.table_discovery_settings import (
    GetTableDiscoverySettingsUseCase,
    GetTableDiscoverySettingsUseCaseInput,
    GetTableDiscoverySettingsUseCaseOutput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_discovery_settings import (
        TableDiscoverySettingsRepo,
    )


class GetTableDiscoverySettingsService(GetTableDiscoverySettingsUseCase):
    """Get the discovery switch."""

    def __init__(self, settings_repo: TableDiscoverySettingsRepo) -> None:
        """Bind the repo."""
        self._settings_repo = settings_repo

    def execute(
        self,
        request: GetTableDiscoverySettingsUseCaseInput,  # noqa: ARG002
    ) -> GetTableDiscoverySettingsUseCaseOutput:
        """Return whether discovery is enabled."""
        settings = self._settings_repo.get_settings()
        return GetTableDiscoverySettingsUseCaseOutput(enabled=settings.enabled, updated_at=settings.updated_at)
