from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListJobsInput:
    """Input for the ListJobs use case — no parameters needed."""
