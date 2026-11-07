"""The Polaris HTTP client, the mapping of Polaris errors and the Iceberg REST mappers every aggregate shares."""

from __future__ import annotations

from context.catalog.adapter.outbound.shared.polaris.iceberg_namespace_path import (
    iceberg_namespace_path,
)
from context.catalog.adapter.outbound.shared.polaris.iceberg_schema_from_polaris import (
    iceberg_schema_from_polaris,
)
from context.catalog.adapter.outbound.shared.polaris.iceberg_schema_to_polaris import (
    iceberg_schema_to_polaris,
)
from context.catalog.adapter.outbound.shared.polaris.iceberg_type_from_polaris import (
    iceberg_type_from_polaris,
)
from context.catalog.adapter.outbound.shared.polaris.iceberg_type_to_polaris import (
    iceberg_type_to_polaris,
)
from context.catalog.adapter.outbound.shared.polaris.listed_identifiers import (
    listed_identifiers,
)
from context.catalog.adapter.outbound.shared.polaris.polaris_error_mapper import (
    raise_for_polaris,
)
from context.catalog.adapter.outbound.shared.polaris.polaris_http_client import (
    PolarisHttpClient,
)
from context.catalog.adapter.outbound.shared.polaris.raise_for_paged_listing import (
    raise_for_paged_listing,
)
from context.catalog.adapter.outbound.shared.polaris.walk_iceberg_namespaces import (
    walk_iceberg_namespaces,
)

__all__ = [
    "PolarisHttpClient",
    "iceberg_namespace_path",
    "iceberg_schema_from_polaris",
    "iceberg_schema_to_polaris",
    "iceberg_type_from_polaris",
    "iceberg_type_to_polaris",
    "listed_identifiers",
    "raise_for_paged_listing",
    "raise_for_polaris",
    "walk_iceberg_namespaces",
]
