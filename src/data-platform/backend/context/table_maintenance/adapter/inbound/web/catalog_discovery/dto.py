"""Define the scanned catalog API DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CatalogScanFailureApiResponse(BaseModel):
    """Describe a scan that could not read its catalog: the credential was refused, or the catalog is gone."""

    reason: Literal["cannot_access", "not_found"]
    detail: str
    failed_at: datetime


class ScannedCatalogApiResponse(BaseModel):
    """Describe a catalog discovery scans: its last completed scan, null before the first, and its current failure.

    ``failure`` is null unless the last failed scan is newer than the last completed one.
    """

    catalog: str
    last_discovered_at: datetime | None
    failure: CatalogScanFailureApiResponse | None


class ScannedCatalogsApiResponse(BaseModel):
    """List the catalogs discovery scans, by name."""

    catalogs: list[ScannedCatalogApiResponse]
