"""Define the CreateMaintenanceRunUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class CreateMaintenanceRunUseCaseInput:
    """Carry the request to create a maintenance run."""

    run_id: str
    table_uuid: str
    trigger: str
    operations: list[str]
    now: datetime
