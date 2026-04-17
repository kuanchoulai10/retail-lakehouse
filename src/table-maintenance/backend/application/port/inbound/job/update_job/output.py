from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class UpdateJobOutput:
    """Output for the UpdateJob use case."""

    id: str
    job_type: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
