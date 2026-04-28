"""Define the CompleteJobRunUseCaseInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompleteJobRunUseCaseInput:
    """Input for completing a job run with success result."""

    run_id: str
    duration_ms: int | None
    metadata: dict[str, str]
