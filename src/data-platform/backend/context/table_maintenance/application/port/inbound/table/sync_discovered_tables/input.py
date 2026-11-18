"""Define the SyncDiscoveredTablesUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class SyncDiscoveredTablesUseCaseInput(UseCaseInput):
    """Carry the request to synchronise the registry with the tables found in the catalog."""

    catalog: str
    namespace: str | None = None
