"""Provide the build_polaris_http_client function."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from context.catalog.adapter.outbound.shared.polaris import PolarisHttpClient

if TYPE_CHECKING:
    from bootstrap.configs import CatalogSettings

_TIMEOUT_SECONDS = 30.0


def build_polaris_http_client(
    settings: CatalogSettings,
    *,
    transport: httpx.BaseTransport | None = None,
) -> PolarisHttpClient:
    """Return the catalog context's Polaris client; it fetches its token on first use, not here."""
    return PolarisHttpClient(
        settings.uri,
        settings.management_uri,
        settings.credential.get_secret_value(),
        settings.scope,
        httpx.Client(timeout=_TIMEOUT_SECONDS, transport=transport),
    )
