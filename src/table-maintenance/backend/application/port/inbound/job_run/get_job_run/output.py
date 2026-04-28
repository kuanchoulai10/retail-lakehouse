"""Define the GetJobRunOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class GetJobRunOutput:
    """Output for the GetJobRun use case."""

    run_id: str
    job_id: str
    status: str
    trigger_type: str
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    result_duration_ms: int | None
    result_metadata: dict[str, str] | None
