"""Define the GetCatalogUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetCatalogUseCaseInput:
    """Name the catalog to get."""

    name: str
