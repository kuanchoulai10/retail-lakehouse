from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetJobInput:
    """Input for the GetJob use case."""

    job_id: str
