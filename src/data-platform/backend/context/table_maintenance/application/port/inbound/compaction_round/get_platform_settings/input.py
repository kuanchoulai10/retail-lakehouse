"""Define the GetPlatformSettingsUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetPlatformSettingsUseCaseInput:
    """Carry the request, which has no fields: there is one platform."""
