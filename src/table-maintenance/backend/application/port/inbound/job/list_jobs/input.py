"""Define the ListJobsUseCaseInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListJobsUseCaseInput:
    """Input for the ListJobs use case — no parameters needed."""
