"""Define the ReleaseCompactionCandidatesUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class ReleaseCompactionCandidatesUseCaseOutput(UseCaseOutput):
    """Say how many candidates were handed back."""

    released: int
