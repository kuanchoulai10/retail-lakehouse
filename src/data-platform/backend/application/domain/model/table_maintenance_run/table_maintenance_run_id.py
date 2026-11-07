"""Define the TableMaintenanceRunId identifier."""

from __future__ import annotations

from dataclasses import dataclass

from base import EntityId


@dataclass(frozen=True)
class TableMaintenanceRunId(EntityId):
    """Identify a TableMaintenanceRun."""
