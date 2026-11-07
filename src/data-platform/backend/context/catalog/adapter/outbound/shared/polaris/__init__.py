"""The Polaris HTTP client and the mapping of Polaris errors, shared by every catalog aggregate's adapter."""

from __future__ import annotations

from context.catalog.adapter.outbound.shared.polaris.iceberg_namespace_path import (
    iceberg_namespace_path,
)
from context.catalog.adapter.outbound.shared.polaris.polaris_error_mapper import (
    raise_for_polaris,
)
from context.catalog.adapter.outbound.shared.polaris.polaris_http_client import (
    PolarisHttpClient,
)

__all__ = [
    "PolarisHttpClient",
    "iceberg_namespace_path",
    "raise_for_polaris",
]
