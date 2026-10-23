"""Define the ReadMaintenanceJobGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadMaintenanceJobGatewayInput:
    """Carry the arguments to read the state of a maintenance job."""

    app_name: str
