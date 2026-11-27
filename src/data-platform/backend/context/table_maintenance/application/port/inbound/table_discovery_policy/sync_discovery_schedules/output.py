"""Define the SyncDiscoverySchedulesUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class SyncDiscoverySchedulesUseCaseOutput(UseCaseOutput):
    """Carry the scanned catalogs, each of which now has its discovery schedule, sorted."""

    catalogs: tuple[str, ...]
