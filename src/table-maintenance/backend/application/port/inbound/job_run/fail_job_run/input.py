"""Define the FailJobRunUseCaseInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FailJobRunUseCaseInput:
    """Input for marking a job run as failed."""

    run_id: str
    error: str
    duration_ms: int | None
    metadata: dict[str, str] | None
