"""Define the GetMaintenanceJobPodsUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetMaintenanceJobPodsUseCaseOutput:
    """Carry the names of the attempt's pods that can still run; empty once they are all gone."""

    live_pods: tuple[str, ...]
