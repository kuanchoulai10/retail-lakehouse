"""Define the DeleteCatalogUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class DeleteCatalogUseCaseInput(UseCaseInput):
    """Name the catalog to delete."""

    name: str
