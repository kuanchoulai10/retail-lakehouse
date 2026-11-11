"""Define the ListCoveredCatalogsUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListCoveredCatalogsUseCaseInput:
    """Carry the request to list the catalogs maintenance covers."""
