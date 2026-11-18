"""Define the ListTablesUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class ListTablesUseCaseInput(UseCaseInput):
    """Name the catalog and the namespace whose tables to list."""

    catalog: str
    namespace: tuple[str, ...]
