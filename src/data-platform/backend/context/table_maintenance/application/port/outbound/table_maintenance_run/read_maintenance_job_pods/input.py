"""Define the ReadMaintenanceJobPodsGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadMaintenanceJobPodsGatewayInput:
    """Carry the attempt whose live pods to read."""

    run_id: str
    operation: str
    attempt: int
