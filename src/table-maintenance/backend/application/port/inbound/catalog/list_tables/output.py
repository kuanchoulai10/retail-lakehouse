"""Define the ListTablesUseCaseOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListTablesUseCaseOutput:
    """Output for the ListTables use case."""

    tables: list[str]
