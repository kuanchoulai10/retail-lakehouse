"""Define the ListTablesUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class ListTablesUseCaseInput(UseCaseInput):
    """Carry the request to list tables, optionally by status."""

    status: str | None = None
