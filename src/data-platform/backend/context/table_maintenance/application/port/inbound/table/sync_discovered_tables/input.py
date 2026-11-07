"""Define the SyncDiscoveredTablesUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SyncDiscoveredTablesUseCaseInput:
    """Carry the request to synchronise the registry with the tables found in the catalog."""

    catalog: str
    namespace: str | None = None
