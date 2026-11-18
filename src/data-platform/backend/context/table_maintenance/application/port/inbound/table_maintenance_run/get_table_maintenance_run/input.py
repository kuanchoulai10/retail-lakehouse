"""Define the GetTableMaintenanceRunUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetTableMaintenanceRunUseCaseInput(UseCaseInput):
    """Carry the request to get one maintenance run."""

    run_id: str
