"""Define the ListGenericTablesUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListGenericTablesUseCaseOutputItem:
    """One generic table of the listing, by identity only."""

    catalog: str
    namespace: list[str]
    name: str


@dataclass(frozen=True)
class ListGenericTablesUseCaseOutput:
    """Carry the listing."""

    items: list[ListGenericTablesUseCaseOutputItem]
