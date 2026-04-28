"""Define the ListTablesUseCaseInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListTablesUseCaseInput:
    """Input for the ListTables use case."""

    namespace: str
