"""Define the MaintenanceRunId identifier."""

from __future__ import annotations

from dataclasses import dataclass

from base.entity_id import EntityId


@dataclass(frozen=True)
class MaintenanceRunId(EntityId):
    """Identify a MaintenanceRun."""
