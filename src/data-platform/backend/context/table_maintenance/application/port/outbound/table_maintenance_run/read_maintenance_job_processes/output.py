"""Define the ReadMaintenanceJobProcessesGatewayOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadMaintenanceJobProcessesGatewayOutput:
    """Carry the names of the attempt's processes that can still run and when its coordinator started.

    ``started_running_at`` is an ISO-8601 time, None while the coordinator has not started.
    """

    live_processes: tuple[str, ...]
    started_running_at: str | None = None
