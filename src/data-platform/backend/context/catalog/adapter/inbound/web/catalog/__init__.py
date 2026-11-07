"""Web adapter for the catalog group."""

from __future__ import annotations

from context.catalog.adapter.inbound.web.catalog.dto import (
    CatalogApiResponse,
    CreateCatalogApiRequest,
    StorageConfigApiRequest,
    StorageConfigApiResponse,
    UpdateCatalogApiRequest,
)
from context.catalog.adapter.inbound.web.catalog.router import router

__all__ = [
    "CatalogApiResponse",
    "CreateCatalogApiRequest",
    "StorageConfigApiRequest",
    "StorageConfigApiResponse",
    "UpdateCatalogApiRequest",
    "router",
]
