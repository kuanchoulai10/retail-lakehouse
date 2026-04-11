from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class GetJobOutput:
    """Output for the GetJob use case — no domain types leak to the adapter."""

    id: str
    job_type: str
    status: str
    created_at: datetime
