"""Define the GetTableDiscoverySettingsUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetTableDiscoverySettingsUseCaseInput:
    """Carry the request to get the discovery switch."""
