"""Provide load_iceberg, which opens a Polaris catalog with PyIceberg as the e2e principal."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyiceberg.catalog import load_catalog

if TYPE_CHECKING:
    from pyiceberg.catalog import Catalog

    from e2e.support.e2e_settings import E2eSettings


def load_iceberg(settings: E2eSettings, warehouse: str) -> Catalog:
    """Open catalog ``warehouse`` for reading and writing tables, with storage on the platform's S3."""
    return load_catalog(
        warehouse,
        type="rest",
        uri=settings.catalog_uri,
        credential=settings.polaris_credential,
        warehouse=warehouse,
        scope=settings.scope,
        **{
            "oauth2-server-uri": f"{settings.catalog_uri}/v1/oauth/tokens",
            "s3.endpoint": settings.s3_endpoint,
            "s3.path-style-access": "true",
            "s3.region": settings.s3_region,
            "s3.access-key-id": settings.s3_access_key_id,
            "s3.secret-access-key": settings.s3_secret_access_key,
        },
    )
