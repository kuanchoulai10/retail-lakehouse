"""Define the DeleteViewUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteViewUseCaseOutput:
    """Signal completion; carries no data."""
