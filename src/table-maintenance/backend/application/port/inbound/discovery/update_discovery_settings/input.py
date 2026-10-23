"""Define the UpdateDiscoverySettingsUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateDiscoverySettingsUseCaseInput:
    """Carry the request to turn discovery on or off."""

    enabled: bool
