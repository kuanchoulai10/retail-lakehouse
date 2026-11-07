"""Define the DeleteTableUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteTableUseCaseOutput:
    """Signal completion; carries no data."""
