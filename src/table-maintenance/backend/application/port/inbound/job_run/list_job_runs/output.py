"""Define the ListJobRunsUseCaseOutput and ListJobRunsUseCaseOutputItem dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class ListJobRunsUseCaseOutputItem:
    """A single run in the ListJobRuns result."""

    run_id: str
    job_id: str
    status: str
    trigger_type: str
    started_at: datetime | None
    finished_at: datetime | None


@dataclass(frozen=True)
class ListJobRunsUseCaseOutput:
    """Output for the ListJobRuns use case."""

    runs: list[ListJobRunsUseCaseOutputItem]
