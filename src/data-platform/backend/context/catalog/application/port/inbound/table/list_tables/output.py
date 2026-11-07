"""Define the ListTablesUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListTablesUseCaseOutputItem:
    """One table of the listing, by identity only."""

    catalog: str
    namespace: list[str]
    name: str


@dataclass(frozen=True)
class ListTablesUseCaseOutput:
    """Carry the listing."""

    items: list[ListTablesUseCaseOutputItem]
