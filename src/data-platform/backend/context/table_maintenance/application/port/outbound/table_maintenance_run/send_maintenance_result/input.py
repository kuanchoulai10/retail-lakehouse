"""Define the SendMaintenanceResultGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SendMaintenanceResultGatewayInput:
    """Carry a maintenance operation result for a run.

    ``execution_ref`` is the execution recorded on the run, never rebuilt
    from ``run_id``.
    """

    execution_ref: str
    run_id: str
    operation: str
    attempt: int
    succeeded: bool
    metrics: dict[str, int]
    error: str | None
