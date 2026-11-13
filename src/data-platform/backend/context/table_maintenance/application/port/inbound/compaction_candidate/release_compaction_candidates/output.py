"""Define the ReleaseCompactionCandidatesUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReleaseCompactionCandidatesUseCaseOutput:
    """Say how many candidates were handed back."""

    released: int
