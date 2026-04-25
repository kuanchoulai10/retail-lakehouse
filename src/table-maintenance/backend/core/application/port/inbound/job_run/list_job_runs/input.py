"""Define the ListJobRunsInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListJobRunsInput:
    """Input for listing JobRuns of a given Job."""

    job_id: str
