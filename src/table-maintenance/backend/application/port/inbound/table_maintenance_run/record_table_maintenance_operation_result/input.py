"""Define the RecordTableMaintenanceOperationResultUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class RecordTableMaintenanceOperationResultUseCaseInput:
    """Carry the request to record the result of a maintenance operation attempt."""

    run_id: str
    operation: str
    attempt: int
    succeeded: bool
    metrics: dict[str, int]
    error: str | None
    now: datetime
