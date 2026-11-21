"""Define the SyncDiscoveredTablesUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class SyncDiscoveredTablesUseCaseOutput(UseCaseOutput):
    """Carry the result of the request to synchronise the registry with the tables found in the catalog.

    ``managed`` counts known tables their discovery policies managed again, ``unmanaged``
    known tables they stopped managing. ``failure`` is the reason (``cannot_access`` or
    ``not_found``) when the scan could not read its catalog, in which case it changed no table.
    """

    registered: int
    renamed: int
    dropped: int
    skipped: int
    ensured: int = 0
    managed: int = 0
    unmanaged: int = 0
    failure: str | None = None
