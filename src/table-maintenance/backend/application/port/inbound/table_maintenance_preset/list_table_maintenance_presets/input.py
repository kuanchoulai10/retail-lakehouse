"""Define the ListTableMaintenancePresetsUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListTableMaintenancePresetsUseCaseInput:
    """Carry the request to list all table maintenance presets."""
