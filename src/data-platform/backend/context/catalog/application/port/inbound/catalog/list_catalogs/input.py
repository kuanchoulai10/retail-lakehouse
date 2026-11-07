"""Define the ListCatalogsUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListCatalogsUseCaseInput:
    """Carry the request to list every catalog."""
