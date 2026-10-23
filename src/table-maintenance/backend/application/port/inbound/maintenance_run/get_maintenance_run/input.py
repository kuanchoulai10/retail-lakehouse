"""Define the GetMaintenanceRunUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetMaintenanceRunUseCaseInput:
    """Carry the request to get one maintenance run."""

    run_id: str
