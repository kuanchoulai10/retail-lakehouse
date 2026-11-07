"""Define the ListNamespacesUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListNamespacesUseCaseInput:
    """Name the catalog and the parent whose direct children to list; an empty parent is the top level."""

    catalog: str
    parent: list[str]
