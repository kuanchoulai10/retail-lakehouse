"""Define the ReadMaintenanceJobPodsGatewayOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadMaintenanceJobPodsGatewayOutput:
    """Carry the names of the attempt's pods that can still run."""

    live_pods: tuple[str, ...]
