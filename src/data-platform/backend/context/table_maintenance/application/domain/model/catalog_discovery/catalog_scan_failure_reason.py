"""Define the CatalogScanFailureReason enumeration."""

from __future__ import annotations

from enum import StrEnum


class CatalogScanFailureReason(StrEnum):
    """Enumerate why a scan could not read a catalog: the credential is refused, or the catalog is gone."""

    CANNOT_ACCESS = "cannot_access"
    NOT_FOUND = "not_found"
