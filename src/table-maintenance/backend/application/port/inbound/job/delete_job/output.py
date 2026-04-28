"""Define the DeleteJobUseCaseOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteJobUseCaseOutput:
    """Output for the DeleteJob use case — empty marker for command completion."""
