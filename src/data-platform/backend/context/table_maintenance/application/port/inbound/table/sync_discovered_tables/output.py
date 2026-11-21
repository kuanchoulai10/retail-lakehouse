"""Define the SyncDiscoveredTablesUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class SyncDiscoveredTablesUseCaseOutput(UseCaseOutput):
    """Carry the result of the request to synchronise the registry with the tables found in the catalog.

    ``managed`` counts known tables their discovery policies managed again, ``unmanaged``
    known tables they stopped managing.
    """

    registered: int
    renamed: int
    dropped: int
    skipped: int
    ensured: int = 0
    managed: int = 0
    unmanaged: int = 0
