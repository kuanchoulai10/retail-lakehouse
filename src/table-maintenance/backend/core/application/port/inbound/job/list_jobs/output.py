"""Define the ListJobsOutput and ListJobsOutputItem dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class ListJobsOutputItem:
    """A single job in the ListJobs result."""

    id: str
    job_type: str
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ListJobsOutput:
    """Output for the ListJobs use case."""

    jobs: list[ListJobsOutputItem]
