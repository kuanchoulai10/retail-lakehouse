"""Define the TableMaintenanceRunId identifier."""

from __future__ import annotations

from typing import ClassVar

from base import EntityId


class TableMaintenanceRunId(EntityId):
    """Identify a TableMaintenanceRun; the reconciliation workflow mints it as an ``mr-`` id."""

    PREFIX: ClassVar[str | None] = "mr"
