"""Define the GetDiscoverySettingsUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetDiscoverySettingsUseCaseInput:
    """Carry the request to get the discovery switch."""
