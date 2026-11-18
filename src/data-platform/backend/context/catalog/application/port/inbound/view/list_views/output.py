"""Define the ListViewsUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class ListViewsUseCaseOutput(UseCaseOutput):
    """Carry the listing."""

    class View(UseCaseOutput):
        """One view of the listing, by identity only."""

        catalog: str
        namespace: tuple[str, ...]
        name: str

    items: tuple[View, ...]
