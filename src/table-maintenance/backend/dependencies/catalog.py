"""Provide the Iceberg catalog client dependency."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

from adapter.outbound.catalog.iceberg_catalog_client import IcebergCatalogClient
from configs import AppSettings
from dependencies.settings import get_settings


@lru_cache(maxsize=1)
def _catalog_client_singleton(uri: str, name: str) -> IcebergCatalogClient:
    """Return a cached IcebergCatalogClient instance."""
    return IcebergCatalogClient(catalog_uri=uri, catalog_name=name)


def get_catalog_client(
    settings: AppSettings = Depends(get_settings),
) -> IcebergCatalogClient:
    """Return a cached IcebergCatalogClient based on AppSettings."""
    return _catalog_client_singleton(
        uri=settings.iceberg_catalog_uri,
        name=settings.iceberg_catalog_name,
    )
