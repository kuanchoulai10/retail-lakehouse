"""Define the ListTablesUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class ListTablesUseCaseOutput(UseCaseOutput):
    """Carry the listing."""

    class Table(UseCaseOutput):
        """One table of the listing, by identity only."""

        catalog: str
        namespace: tuple[str, ...]
        name: str

    items: tuple[Table, ...]
