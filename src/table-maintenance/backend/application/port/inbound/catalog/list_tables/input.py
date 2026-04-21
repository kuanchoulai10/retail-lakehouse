"""Define the ListTablesInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListTablesInput:
    """Input for the ListTables use case."""

    namespace: str
