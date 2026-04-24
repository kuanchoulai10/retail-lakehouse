"""Define the CreateJobOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class CreateJobOutput:
    """Output for the CreateJob use case."""

    id: str
    job_type: str
    status: str
    created_at: datetime
    updated_at: datetime
