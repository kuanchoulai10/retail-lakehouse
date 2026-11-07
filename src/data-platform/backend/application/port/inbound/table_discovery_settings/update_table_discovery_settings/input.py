"""Define the UpdateTableDiscoverySettingsUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateTableDiscoverySettingsUseCaseInput:
    """Carry the request to turn discovery on or off."""

    enabled: bool
