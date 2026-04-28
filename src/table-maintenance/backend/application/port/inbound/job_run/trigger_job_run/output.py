"""Define the TriggerJobRunUseCaseOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TriggerJobRunUseCaseOutput:
    """Output of the trigger-job-run use case (async — no run_id yet)."""

    job_id: str
    accepted: bool = True
