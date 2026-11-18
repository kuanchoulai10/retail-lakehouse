"""Define the ListTableMaintenanceRunsUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class ListTableMaintenanceRunsUseCaseInput(UseCaseInput):
    """Carry the request to list the maintenance runs of a table."""

    table_uuid: str
    limit: int = 50
