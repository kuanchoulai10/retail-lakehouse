"""Define the ListMaintenanceRunsUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListMaintenanceRunsUseCaseInput:
    """Carry the request to list the maintenance runs of a table."""

    table_uuid: str
    limit: int = 50
