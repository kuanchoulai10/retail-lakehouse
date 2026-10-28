"""Define the TableMetadataRef."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableMetadataRef:
    """Locate a table by catalog, dot-joined namespace and table name."""

    catalog: str
    namespace: str
    table: str
