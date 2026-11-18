"""Define the ListGenericTablesUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class ListGenericTablesUseCaseInput(UseCaseInput):
    """Name the catalog and the namespace whose generic tables to list."""

    catalog: str
    namespace: tuple[str, ...]
