"""Define the RecordMaintenanceOperationResultUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecordMaintenanceOperationResultUseCaseOutput:
    """Carry the result of the request to record the result of a maintenance operation attempt."""

    run_id: str
    status: str
