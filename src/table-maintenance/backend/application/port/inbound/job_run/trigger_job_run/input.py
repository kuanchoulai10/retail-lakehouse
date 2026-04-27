"""Define the TriggerJobRunInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TriggerJobRunInput:
    """Input for triggering a new JobRun for an existing Job."""

    job_id: str
