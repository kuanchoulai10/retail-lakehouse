"""Grant a new catalog's admin role the right to manage the catalog's content."""

from context.catalog.application.port.outbound.catalog.create_catalog_content_grant.gateway import (
    CreateCatalogContentGrantGateway,
)
from context.catalog.application.port.outbound.catalog.create_catalog_content_grant.input import (
    CreateCatalogContentGrantGatewayInput,
)

__all__ = ["CreateCatalogContentGrantGateway", "CreateCatalogContentGrantGatewayInput"]
