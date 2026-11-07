"""Define the DeleteGenericTableUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteGenericTableUseCaseOutput:
    """Signal completion; carries no data."""
