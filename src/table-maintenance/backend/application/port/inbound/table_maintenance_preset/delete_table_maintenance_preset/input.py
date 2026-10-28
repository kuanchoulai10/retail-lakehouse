"""Define the DeleteTableMaintenancePresetUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteTableMaintenancePresetUseCaseInput:
    """Carry the request to delete a table maintenance preset that no rule references."""

    id: str
