"""Define the ProcessTableMaintenanceCallbackUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessTableMaintenanceCallbackUseCaseInput:
    """Carry the request to forward a Spark job result callback to the workflow."""

    run_id: str
    operation: str
    attempt: int
    succeeded: bool
    metrics: dict[str, int]
    error: str | None
