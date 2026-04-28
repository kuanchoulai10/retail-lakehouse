"""Define the CompleteJobRunInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompleteJobRunInput:
    """Input for completing a job run with success result."""

    run_id: str
    duration_ms: int | None
    metadata: dict[str, str]
