"""Define the discovery router."""

from __future__ import annotations

from typing import Annotated

from adapter.inbound.web.table_discovery_settings.dto import (
    TableDiscoverySettingsApiResponse,
    ScanDiscoveryApiRequest,
    ScanDiscoveryApiResponse,
    UpdateTableDiscoverySettingsApiRequest,
)
from adapter.inbound.web.shared import WebUseCases, use_cases_dependency
from application.port.inbound.table_discovery_settings import (
    GetTableDiscoverySettingsUseCaseInput,
    UpdateTableDiscoverySettingsUseCaseInput,
)
from application.port.inbound.table import SyncDiscoveredTablesUseCaseInput
from fastapi import APIRouter, Depends, status

router = APIRouter(
    prefix="/table-discovery-settings", tags=["table-discovery-settings"]
)

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]


@router.get("")
def get_table_discovery_settings(
    use_cases: UseCases,
) -> TableDiscoverySettingsApiResponse:
    """Return whether discovery is enabled."""
    output = use_cases.get_table_discovery_settings.execute(
        GetTableDiscoverySettingsUseCaseInput()
    )
    return TableDiscoverySettingsApiResponse.model_validate(output)


@router.put("")
def update_table_discovery_settings(
    body: UpdateTableDiscoverySettingsApiRequest, use_cases: UseCases
) -> TableDiscoverySettingsApiResponse:
    """Switch discovery on or off."""
    output = use_cases.update_table_discovery_settings.execute(
        UpdateTableDiscoverySettingsUseCaseInput(enabled=body.enabled)
    )
    return TableDiscoverySettingsApiResponse.model_validate(output)


@router.post("/scan", status_code=status.HTTP_202_ACCEPTED)
def scan_discovery(
    body: ScanDiscoveryApiRequest, use_cases: UseCases
) -> ScanDiscoveryApiResponse:
    """Scan a catalog, or one namespace, for tables to manage."""
    output = use_cases.sync_discovered_tables.execute(
        SyncDiscoveredTablesUseCaseInput(catalog=body.catalog, namespace=body.namespace)
    )
    return ScanDiscoveryApiResponse.model_validate(output)
