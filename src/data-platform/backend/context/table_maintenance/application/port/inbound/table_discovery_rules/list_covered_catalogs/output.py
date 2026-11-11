"""Define the ListCoveredCatalogsUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListCoveredCatalogsUseCaseOutput:
    """Report the names of the catalogs maintenance covers."""

    catalogs: list[str]
