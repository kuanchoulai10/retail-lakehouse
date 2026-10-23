"""Define the OperationResultSignal workflow contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OperationResultSignal:
    """Payload of the operation_result signal sent to a maintenance workflow."""

    run_id: str
    operation: str
    attempt: int
    succeeded: bool
    metrics: dict
    error: str | None
