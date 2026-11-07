"""Define the ListTablesUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListTablesUseCaseInput:
    """Name the catalog and the namespace whose tables to list."""

    catalog: str
    namespace: list[str]
