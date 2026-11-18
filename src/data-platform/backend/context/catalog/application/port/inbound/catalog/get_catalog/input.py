"""Define the GetCatalogUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetCatalogUseCaseInput(UseCaseInput):
    """Name the catalog to get."""

    name: str
