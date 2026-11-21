"""Define the CatalogScanFailure value object."""

from __future__ import annotations

from datetime import datetime

from base import ValueObject
from context.table_maintenance.application.domain.model.catalog_discovery.catalog_scan_failure_reason import (
    CatalogScanFailureReason,
)


class CatalogScanFailure(ValueObject):
    """Record a scan that could not read its catalog: why, the catalog's own words, and when the scan started."""

    reason: CatalogScanFailureReason
    detail: str
    failed_at: datetime
