"""Define the SubmitMaintenanceOperationUseCaseInput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseInput


class SubmitMaintenanceOperationUseCaseInput(UseCaseInput):
    """Carry the request to submit one attempt of a maintenance operation to Spark."""

    class Filter(UseCaseInput):
        """One where clause of a compaction, per partition spec; empty means all."""

        spec_id: int
        where: str

    run_id: str
    operation: str
    attempt: int
    filters: tuple[Filter, ...]
    procedure_args: dict[str, Any]
    callback_base_url: str
    now: datetime
    size: str = "S"
