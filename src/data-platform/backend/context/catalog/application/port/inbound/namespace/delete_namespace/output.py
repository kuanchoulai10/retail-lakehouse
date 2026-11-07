"""Define the DeleteNamespaceUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteNamespaceUseCaseOutput:
    """Signal completion; carries no data."""
