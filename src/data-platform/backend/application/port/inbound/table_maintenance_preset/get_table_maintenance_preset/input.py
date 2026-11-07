"""Define the GetTableMaintenancePresetUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetTableMaintenancePresetUseCaseInput:
    """Carry the request to get one table maintenance preset."""

    id: str
