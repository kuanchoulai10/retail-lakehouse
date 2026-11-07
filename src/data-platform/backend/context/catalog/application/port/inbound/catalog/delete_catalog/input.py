"""Define the DeleteCatalogUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteCatalogUseCaseInput:
    """Name the catalog to delete."""

    name: str
