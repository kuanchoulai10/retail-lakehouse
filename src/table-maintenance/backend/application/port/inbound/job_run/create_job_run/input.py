from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CreateJobRunInput:
    """Input for triggering a new JobRun for an existing Job."""

    job_id: str
