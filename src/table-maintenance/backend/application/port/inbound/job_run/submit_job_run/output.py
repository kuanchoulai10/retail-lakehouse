"""Define the SubmitJobRunUseCaseOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubmitJobRunUseCaseOutput:
    """Output for the submit job run use case.

    Currently empty — the use case is fire-and-forget.
    """
