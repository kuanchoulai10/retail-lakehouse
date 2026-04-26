"""Define the ListTablesOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListTablesOutput:
    """Output for the ListTables use case."""

    tables: list[str]
