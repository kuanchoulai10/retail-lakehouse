"""Define the CreateCatalogContentGrantPolarisGateway."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.adapter.outbound.catalog.polaris.management_catalog_path import (
    management_catalog_path,
)
from context.catalog.application.port.outbound.catalog import (
    CreateCatalogContentGrantGateway,
)

if TYPE_CHECKING:
    from context.catalog.adapter.outbound.shared.polaris import PolarisHttpClient
    from context.catalog.application.port.outbound.catalog import (
        CreateCatalogContentGrantGatewayInput,
    )

_GRANT = {"grant": {"type": "catalog", "privilege": "CATALOG_MANAGE_CONTENT"}}


class CreateCatalogContentGrantPolarisGateway(CreateCatalogContentGrantGateway):
    """Grant CATALOG_MANAGE_CONTENT to the catalog's ``catalog_admin`` role through the management API.

    Polaris creates ``catalog_admin`` with every catalog but without this privilege; it is
    the same grant the platform's create-catalog job makes for the bootstrapped catalog.
    """

    def __init__(self, polaris: PolarisHttpClient) -> None:
        """Bind the Polaris client."""
        self._polaris = polaris

    def create(self, input: CreateCatalogContentGrantGatewayInput) -> None:  # noqa: A002
        """PUT the grant on the catalog's catalog_admin role."""
        path = f"{management_catalog_path(input.catalog_name)}/catalog-roles/catalog_admin/grants"
        self._polaris.management_request("PUT", path, json=_GRANT)
