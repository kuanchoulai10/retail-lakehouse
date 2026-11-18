"""Define the ListViewsUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class ListViewsUseCaseInput(UseCaseInput):
    """Name the catalog and the namespace whose views to list."""

    catalog: str
    namespace: tuple[str, ...]
