"""Define the ListCoveredCatalogsUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class ListCoveredCatalogsUseCaseOutput(UseCaseOutput):
    """Report the names of the catalogs maintenance covers."""

    catalogs: tuple[str, ...]
