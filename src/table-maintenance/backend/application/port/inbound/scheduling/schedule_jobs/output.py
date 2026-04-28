"""Define the result of a scheduling tick."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScheduleJobsUseCaseOutput:
    """Result returned after one scheduling tick."""

    triggered_count: int = 0
    job_ids: list[str] = field(default_factory=list)
