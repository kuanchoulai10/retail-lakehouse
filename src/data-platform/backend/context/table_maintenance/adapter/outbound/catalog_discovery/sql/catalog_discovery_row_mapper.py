"""Define the CatalogDiscoveryRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.port.outbound.catalog_discovery import (
    CatalogDiscovery,
    CatalogDiscoveryId,
    CatalogScanFailure,
    CatalogScanFailureReason,
)

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


class CatalogDiscoveryRowMapper:
    """Map a CatalogDiscovery to its row and back; the failure's three columns are all set or all NULL."""

    @staticmethod
    def to_values(discovery: CatalogDiscovery) -> dict[str, Any]:
        """Return the column values of the discovery's row."""
        return {
            "catalog": discovery.catalog,
            "last_discovered_at": discovery.last_discovered_at,
            **CatalogDiscoveryRowMapper.failure_values(discovery.last_failure),
        }

    @staticmethod
    def failure_values(failure: CatalogScanFailure | None) -> dict[str, Any]:
        """Return the failure's column values, all None for no failure."""
        if failure is None:
            return {"failure_reason": None, "failure_detail": None, "failed_at": None}
        return {
            "failure_reason": failure.reason.value,
            "failure_detail": failure.detail,
            "failed_at": failure.failed_at,
        }

    @staticmethod
    def to_aggregate(row: RowMapping) -> CatalogDiscovery:
        """Rebuild the discovery from its row."""
        failure = (
            None
            if row["failed_at"] is None
            else CatalogScanFailure(
                reason=CatalogScanFailureReason(row["failure_reason"]),
                detail=row["failure_detail"],
                failed_at=row["failed_at"],
            )
        )
        return CatalogDiscovery(
            id=CatalogDiscoveryId(row["catalog"]),
            last_discovered_at=row["last_discovered_at"],
            last_failure=failure,
        )
