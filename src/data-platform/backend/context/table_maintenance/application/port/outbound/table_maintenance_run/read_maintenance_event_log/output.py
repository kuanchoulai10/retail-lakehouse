"""Define the ReadMaintenanceEventLogGatewayOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadMaintenanceEventLogGatewayOutput:
    """Carry whether the event log finished: True, False when it was left open, None when it is not found."""

    finished: bool | None
