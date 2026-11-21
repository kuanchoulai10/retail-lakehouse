"""Define the ListScannedCatalogsUseCaseOutput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseOutput


class ListScannedCatalogsUseCaseOutput(UseCaseOutput):
    """Carry the catalogs discovery scans, sorted by name, each with its scan state."""

    class Failure(UseCaseOutput):
        """A scan that could not read the catalog: ``cannot_access`` or ``not_found``, the detail, and when."""

        reason: str
        detail: str
        failed_at: datetime

    class ScannedCatalog(UseCaseOutput):
        """One scanned catalog: its last completed scan, None before the first, and its current failure.

        ``failure`` is None unless the last failure is newer than the last completed scan.
        """

        catalog: str
        last_discovered_at: datetime | None
        failure: ListScannedCatalogsUseCaseOutput.Failure | None

    catalogs: tuple[ScannedCatalog, ...]
