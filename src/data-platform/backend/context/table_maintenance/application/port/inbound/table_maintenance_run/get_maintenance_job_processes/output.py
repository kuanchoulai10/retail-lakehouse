"""Define the GetMaintenanceJobProcessesUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class GetMaintenanceJobProcessesUseCaseOutput(UseCaseOutput):
    """Carry the names of the attempt's processes that can still run; empty once they are all gone."""

    live_processes: tuple[str, ...]
