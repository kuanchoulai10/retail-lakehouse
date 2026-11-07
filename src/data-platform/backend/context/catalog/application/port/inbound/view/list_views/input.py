"""Define the ListViewsUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListViewsUseCaseInput:
    """Name the catalog and the namespace whose views to list."""

    catalog: str
    namespace: list[str]
