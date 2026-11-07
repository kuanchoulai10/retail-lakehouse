"""Define the DeleteCatalogUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteCatalogUseCaseOutput:
    """Signal completion; carries no data."""
