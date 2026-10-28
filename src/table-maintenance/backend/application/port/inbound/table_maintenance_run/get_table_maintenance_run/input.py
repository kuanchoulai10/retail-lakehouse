"""Define the GetTableMaintenanceRunUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetTableMaintenanceRunUseCaseInput:
    """Carry the request to get one maintenance run."""

    run_id: str
