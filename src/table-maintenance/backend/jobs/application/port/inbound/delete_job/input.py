from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteJobInput:
    """Input for the DeleteJob use case."""

    job_id: str
