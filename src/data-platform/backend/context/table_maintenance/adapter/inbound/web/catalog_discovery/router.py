"""Define the scanned catalogs router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from context.table_maintenance.adapter.inbound.web.catalog_discovery.dto import (
    CatalogScanFailureApiResponse,
    ScannedCatalogApiResponse,
    ScannedCatalogsApiResponse,
)
from context.table_maintenance.adapter.inbound.web.shared import WebUseCases, use_cases_dependency
from context.table_maintenance.application.port.inbound.catalog_discovery import ListScannedCatalogsUseCaseInput

router = APIRouter(tags=["discovery-policies"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]


@router.get("/scanned-catalogs")
def list_scanned_catalogs(use_cases: UseCases) -> ScannedCatalogsApiResponse:
    """List the catalogs a managing discovery policy is attached in, with each one's last scan and current failure."""
    output = use_cases.list_scanned_catalogs.execute(ListScannedCatalogsUseCaseInput())
    return ScannedCatalogsApiResponse(
        catalogs=[
            ScannedCatalogApiResponse(
                catalog=item.catalog,
                last_discovered_at=item.last_discovered_at,
                failure=None
                if item.failure is None
                else CatalogScanFailureApiResponse.model_validate(item.failure.model_dump()),
            )
            for item in output.catalogs
        ]
    )
