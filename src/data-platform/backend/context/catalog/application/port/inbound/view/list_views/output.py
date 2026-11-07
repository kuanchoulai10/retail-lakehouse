"""Define the ListViewsUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListViewsUseCaseOutputItem:
    """One view of the listing, by identity only."""

    catalog: str
    namespace: list[str]
    name: str


@dataclass(frozen=True)
class ListViewsUseCaseOutput:
    """Carry the listing."""

    items: list[ListViewsUseCaseOutputItem]
