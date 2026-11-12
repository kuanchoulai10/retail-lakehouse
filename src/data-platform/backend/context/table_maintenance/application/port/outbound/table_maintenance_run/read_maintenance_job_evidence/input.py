"""Define the ReadMaintenanceJobEvidenceGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadMaintenanceJobEvidenceGatewayInput:
    """Carry the attempt whose failure evidence to read."""

    run_id: str
    operation: str
    attempt: int
