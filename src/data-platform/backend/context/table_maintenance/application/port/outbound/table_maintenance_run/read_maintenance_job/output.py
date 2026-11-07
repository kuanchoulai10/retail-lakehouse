"""Define the ReadMaintenanceJobGatewayOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadMaintenanceJobGatewayOutput:
    """Carry the result of the request to read the state of a maintenance job."""

    state: str
    error: str | None = None
