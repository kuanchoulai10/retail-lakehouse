"""Define the ListGenericTablesUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class ListGenericTablesUseCaseOutput(UseCaseOutput):
    """Carry the listing."""

    class GenericTable(UseCaseOutput):
        """One generic table of the listing, by identity only."""

        catalog: str
        namespace: tuple[str, ...]
        name: str

    items: tuple[GenericTable, ...]
