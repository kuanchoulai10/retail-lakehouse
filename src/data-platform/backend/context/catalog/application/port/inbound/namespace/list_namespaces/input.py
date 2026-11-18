"""Define the ListNamespacesUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class ListNamespacesUseCaseInput(UseCaseInput):
    """Name the catalog and the parent whose direct children to list; an empty parent is the top level."""

    catalog: str
    parent: tuple[str, ...]
