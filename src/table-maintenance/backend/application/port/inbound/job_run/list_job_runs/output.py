"""Define the ListJobRunsOutput and ListJobRunsOutputItem dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class ListJobRunsOutputItem:
    """A single run in the ListJobRuns result."""

    run_id: str
    job_id: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None


@dataclass(frozen=True)
class ListJobRunsOutput:
    """Output for the ListJobRuns use case."""

    runs: list[ListJobRunsOutputItem]
