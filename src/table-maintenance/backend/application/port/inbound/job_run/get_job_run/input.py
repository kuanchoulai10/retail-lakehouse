"""Define the GetJobRunInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetJobRunInput:
    """Input for retrieving a specific JobRun by id."""

    run_id: str
