"""Define the TableMaintenanceRunId identifier."""

from __future__ import annotations

from typing import ClassVar

from base import EntityId


class TableMaintenanceRunId(EntityId):
    """Identify a TableMaintenanceRun; an ``mr-`` id the application issues (ADR 0015)."""

    PREFIX: ClassVar[str | None] = "mr"
