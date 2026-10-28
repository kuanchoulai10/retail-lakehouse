"""Define the ListTablesUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListTablesUseCaseInput:
    """Carry the request to list tables, optionally by status."""

    status: str | None = None
