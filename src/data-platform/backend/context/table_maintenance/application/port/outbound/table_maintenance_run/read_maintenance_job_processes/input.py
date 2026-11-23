"""Define the ReadMaintenanceJobProcessesGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadMaintenanceJobProcessesGatewayInput:
    """Carry the attempt whose live processes to read."""

    run_id: str
    operation: str
    attempt: int
