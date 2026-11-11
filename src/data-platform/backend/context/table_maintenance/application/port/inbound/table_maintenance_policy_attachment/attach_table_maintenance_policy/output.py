"""Define the AttachTableMaintenancePolicyUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class AttachTableMaintenancePolicyUseCaseOutput:
    """Carry the outcome of the request."""

    target_type: str
    path: tuple[str, ...]
    table_uuid: str | None
    policy_name: str
    attached_at: datetime
