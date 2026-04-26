"""Provide the Iceberg catalog reader dependency."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

from adapter.outbound.catalog.iceberg_catalog_client import IcebergCatalogClient
from application.port.outbound.catalog.catalog_reader import CatalogReader
from core.configs import AppSettings
from dependencies.settings import get_settings


@lru_cache(maxsize=1)
def _catalog_client_singleton(
    uri: str, name: str, credential: str, warehouse: str, scope: str
) -> IcebergCatalogClient:
    """Return a cached IcebergCatalogClient instance."""
    return IcebergCatalogClient(
        catalog_uri=uri,
        catalog_name=name,
        credential=credential,
        warehouse=warehouse,
        scope=scope,
    )


def get_catalog_reader(
    settings: AppSettings = Depends(get_settings),
) -> CatalogReader:
    """Return a CatalogReader backed by IcebergCatalogClient."""
    return _catalog_client_singleton(
        uri=settings.iceberg_catalog_uri,
        name=settings.iceberg_catalog_name,
        credential=settings.iceberg_catalog_credential,
        warehouse=settings.iceberg_catalog_warehouse,
        scope=settings.iceberg_catalog_scope,
    )
