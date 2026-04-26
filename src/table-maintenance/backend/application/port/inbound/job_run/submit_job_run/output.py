"""Define the SubmitJobRunOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubmitJobRunOutput:
    """Output for the submit job run use case.

    Currently empty — the use case is fire-and-forget.
    """
