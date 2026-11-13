"""Define the GetSchedulerSettingsUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetSchedulerSettingsUseCaseInput:
    """Carry the request, which has no fields: there is one scheduler."""
