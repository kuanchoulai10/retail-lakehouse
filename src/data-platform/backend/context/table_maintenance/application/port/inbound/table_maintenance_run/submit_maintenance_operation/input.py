"""Define the SubmitMaintenanceOperationUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any


@dataclass(frozen=True)
class SubmitMaintenanceOperationUseCaseInputFilterItem:
    """One where clause of a compaction, per partition spec; empty means all."""

    spec_id: int
    where: str


@dataclass(frozen=True)
class SubmitMaintenanceOperationUseCaseInput:
    """Carry the request to submit one attempt of a maintenance operation to Spark."""

    run_id: str
    operation: str
    attempt: int
    filters: list[SubmitMaintenanceOperationUseCaseInputFilterItem]
    procedure_args: dict[str, Any]
    callback_base_url: str
    now: datetime
