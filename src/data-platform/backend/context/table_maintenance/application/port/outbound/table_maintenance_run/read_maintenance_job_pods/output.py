"""Define the ReadMaintenanceJobPodsGatewayOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadMaintenanceJobPodsGatewayOutput:
    """Carry the names of the attempt's pods that can still run and when its driver started.

    ``driver_started_at`` is an ISO-8601 time, None while the driver has not started.
    """

    live_pods: tuple[str, ...]
    driver_started_at: str | None = None
