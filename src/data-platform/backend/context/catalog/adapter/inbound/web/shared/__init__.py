"""Web adapter pieces shared by every catalog aggregate router: use cases, their dependency, schema DTOs."""

from __future__ import annotations

from context.catalog.adapter.inbound.web.shared.schema_api_response import SchemaApiResponse
from context.catalog.adapter.inbound.web.shared.schema_field_api_response import SchemaFieldApiResponse
from context.catalog.adapter.inbound.web.shared.use_cases_dependency import (
    use_cases_dependency,
)
from context.catalog.adapter.inbound.web.shared.web_use_cases import WebUseCases

__all__ = [
    "SchemaApiResponse",
    "SchemaFieldApiResponse",
    "WebUseCases",
    "use_cases_dependency",
]
