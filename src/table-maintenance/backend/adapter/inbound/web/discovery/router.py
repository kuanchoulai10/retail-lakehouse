"""Define the discovery router."""

from __future__ import annotations

from typing import Annotated

from adapter.inbound.web.discovery.dto import (
    DiscoverySettingsApiResponse,
    ScanDiscoveryApiRequest,
    ScanDiscoveryApiResponse,
    UpdateDiscoverySettingsApiRequest,
)
from adapter.inbound.web.use_cases_dependency import web_use_cases
from adapter.inbound.web.web_use_cases import WebUseCases
from application.port.inbound.discovery.get_discovery_settings import (
    GetDiscoverySettingsUseCaseInput,
)
from application.port.inbound.discovery.sync_discovered_tables import (
    SyncDiscoveredTablesUseCaseInput,
)
from application.port.inbound.discovery.update_discovery_settings import (
    UpdateDiscoverySettingsUseCaseInput,
)
from fastapi import APIRouter, Depends, status

router = APIRouter(prefix="/discovery", tags=["discovery"])

UseCases = Annotated[WebUseCases, Depends(web_use_cases)]


@router.get("")
def get_discovery_settings(use_cases: UseCases) -> DiscoverySettingsApiResponse:
    """Return whether discovery is enabled."""
    output = use_cases.get_discovery_settings.execute(
        GetDiscoverySettingsUseCaseInput()
    )
    return DiscoverySettingsApiResponse.model_validate(output)


@router.put("")
def update_discovery_settings(
    body: UpdateDiscoverySettingsApiRequest, use_cases: UseCases
) -> DiscoverySettingsApiResponse:
    """Switch discovery on or off."""
    output = use_cases.update_discovery_settings.execute(
        UpdateDiscoverySettingsUseCaseInput(enabled=body.enabled)
    )
    return DiscoverySettingsApiResponse.model_validate(output)


@router.post("/scan", status_code=status.HTTP_202_ACCEPTED)
def scan_discovery(
    body: ScanDiscoveryApiRequest, use_cases: UseCases
) -> ScanDiscoveryApiResponse:
    """Scan a catalog, or one namespace, for tables to manage."""
    output = use_cases.sync_discovered_tables.execute(
        SyncDiscoveredTablesUseCaseInput(catalog=body.catalog, namespace=body.namespace)
    )
    return ScanDiscoveryApiResponse.model_validate(output)
