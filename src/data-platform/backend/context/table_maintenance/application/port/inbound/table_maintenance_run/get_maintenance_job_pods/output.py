"""Define the GetMaintenanceJobPodsUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class GetMaintenanceJobPodsUseCaseOutput(UseCaseOutput):
    """Carry the names of the attempt's pods that can still run; empty once they are all gone."""

    live_pods: tuple[str, ...]
