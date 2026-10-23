"""Define the GetDiscoverySettingsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound.discovery.get_discovery_settings import (
    GetDiscoverySettingsUseCase,
    GetDiscoverySettingsUseCaseInput,
    GetDiscoverySettingsUseCaseOutput,
)

if TYPE_CHECKING:
    from application.port.outbound.discovery.discovery_settings_repo import (
        DiscoverySettingsRepo,
    )


class GetDiscoverySettingsService(GetDiscoverySettingsUseCase):
    """Get the discovery switch."""

    def __init__(self, settings_repo: DiscoverySettingsRepo) -> None:
        """Bind the repo."""
        self._settings_repo = settings_repo

    def execute(
        self,
        request: GetDiscoverySettingsUseCaseInput,  # noqa: ARG002
    ) -> GetDiscoverySettingsUseCaseOutput:
        """Return whether discovery is enabled."""
        settings = self._settings_repo.get_settings()
        return GetDiscoverySettingsUseCaseOutput(
            enabled=settings.enabled, updated_at=settings.updated_at
        )
