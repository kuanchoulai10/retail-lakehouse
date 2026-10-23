"""Define the ListManagedTablesUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListManagedTablesUseCaseInput:
    """Carry the request to list managed tables, optionally by status."""

    status: str | None = None
