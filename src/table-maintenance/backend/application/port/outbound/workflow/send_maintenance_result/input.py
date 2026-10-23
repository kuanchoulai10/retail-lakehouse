"""Define the SendMaintenanceResultGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SendMaintenanceResultGatewayInput:
    """Carry the arguments to send a maintenance result to the workflow."""

    run_id: str
    operation: str
    attempt: int
    succeeded: bool
    metrics: dict[str, int]
    error: str | None
