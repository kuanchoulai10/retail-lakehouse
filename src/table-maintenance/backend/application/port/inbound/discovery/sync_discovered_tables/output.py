"""Define the SyncDiscoveredTablesUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SyncDiscoveredTablesUseCaseOutput:
    """Carry the result of the request to synchronise the registry with the tables found in the catalog."""

    registered: int
    renamed: int
    dropped: int
    skipped: int
