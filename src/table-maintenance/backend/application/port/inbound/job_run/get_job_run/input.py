"""Define the GetJobRunUseCaseInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetJobRunUseCaseInput:
    """Input for retrieving a specific JobRun by id."""

    run_id: str
