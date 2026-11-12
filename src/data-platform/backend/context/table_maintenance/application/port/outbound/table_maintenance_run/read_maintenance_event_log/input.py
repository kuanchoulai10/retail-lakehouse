"""Define the ReadMaintenanceEventLogGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadMaintenanceEventLogGatewayInput:
    """Carry the execution whose event log to read."""

    execution_id: str
