"""Define the CatalogDiscovery aggregate root."""

from __future__ import annotations

from datetime import datetime

from pydantic import model_validator

from base import AggregateRoot
from context.table_maintenance.application.domain.model.catalog_discovery.catalog_scan_failure import (
    CatalogScanFailure,
)
from context.table_maintenance.application.domain.model.shared import CatalogDiscoveryId


class CatalogDiscovery(AggregateRoot[CatalogDiscoveryId]):
    """Remember when discovery last scanned one whole catalog, and when a scan last could not read it.

    A catalog-wide scan sees every live table of the catalog, so its time is the
    last time each of them was discovered; recording it once per scan spares
    saving every table on every scan. A scan of one namespace is not recorded,
    since it does not see the rest of the catalog.

    A scan, catalog-wide or of one namespace, that the catalog refuses or no longer
    knows records a ``CatalogScanFailure`` instead. The two times move forward
    independently, and the failure is current only while it is newer than the last
    completed scan, so a later good scan clears it without deleting it.
    """

    id: CatalogDiscoveryId
    last_discovered_at: datetime | None = None
    last_failure: CatalogScanFailure | None = None

    @model_validator(mode="after")
    def _names_a_catalog(self) -> CatalogDiscovery:
        if not self.id.value:
            raise ValueError("a catalog discovery needs a catalog name")
        return self

    @model_validator(mode="after")
    def _holds_a_scan_or_a_failure(self) -> CatalogDiscovery:
        if self.last_discovered_at is None and self.last_failure is None:
            raise ValueError("a catalog discovery records a completed scan, a failed one, or both")
        return self

    @classmethod
    def first(cls, catalog: str, at: datetime) -> CatalogDiscovery:
        """Record the first scan of ``catalog``, which started at ``at``."""
        return cls(id=CatalogDiscoveryId(catalog), last_discovered_at=at)

    @classmethod
    def failed(cls, catalog: str, failure: CatalogScanFailure) -> CatalogDiscovery:
        """Record a scan of ``catalog`` that could not read it, the first record of that catalog."""
        return cls(id=CatalogDiscoveryId(catalog), last_failure=failure)

    @property
    def catalog(self) -> str:
        """Return the name of the catalog scanned."""
        return self.id.value

    @property
    def current_failure(self) -> CatalogScanFailure | None:
        """Return the last failure while it is newer than the last completed scan, else None."""
        failure = self.last_failure
        if failure is None:
            return None
        if self.last_discovered_at is not None and failure.failed_at <= self.last_discovered_at:
            return None
        return failure

    def record(self, at: datetime) -> None:
        """Record a scan that started at ``at``; the time never moves back."""
        self.last_discovered_at = at if self.last_discovered_at is None else max(self.last_discovered_at, at)

    def record_failure(self, failure: CatalogScanFailure) -> None:
        """Record a scan that could not read the catalog; an older failure never replaces a newer one."""
        if self.last_failure is None or failure.failed_at > self.last_failure.failed_at:
            self.last_failure = failure
