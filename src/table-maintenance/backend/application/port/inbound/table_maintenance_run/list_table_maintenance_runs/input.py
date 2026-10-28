"""Define the ListTableMaintenanceRunsUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListTableMaintenanceRunsUseCaseInput:
    """Carry the request to list the maintenance runs of a table."""

    table_uuid: str
    limit: int = 50
