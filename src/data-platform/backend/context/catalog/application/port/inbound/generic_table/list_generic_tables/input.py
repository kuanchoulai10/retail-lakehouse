"""Define the ListGenericTablesUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListGenericTablesUseCaseInput:
    """Name the catalog and the namespace whose generic tables to list."""

    catalog: str
    namespace: list[str]
