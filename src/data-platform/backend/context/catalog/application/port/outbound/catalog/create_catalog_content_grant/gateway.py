"""Define the CreateCatalogContentGrantGateway outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Gateway

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.catalog.create_catalog_content_grant.input import (
        CreateCatalogContentGrantGatewayInput,
    )


class CreateCatalogContentGrantGateway(Gateway):
    """Let a catalog's own admin role manage the catalog's content (namespaces, tables, views)."""

    @abstractmethod
    def create(self, input: CreateCatalogContentGrantGatewayInput) -> None:  # noqa: A002
        """Grant the content privilege on the named catalog to that catalog's admin role."""
