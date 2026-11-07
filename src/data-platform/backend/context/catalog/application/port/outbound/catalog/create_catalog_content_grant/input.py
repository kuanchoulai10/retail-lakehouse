"""Define the CreateCatalogContentGrantGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CreateCatalogContentGrantGatewayInput:
    """Name the catalog whose admin role gets the content privilege."""

    catalog_name: str
