"""Web adapter for the namespace group."""

from __future__ import annotations

from context.catalog.adapter.inbound.web.namespace.dto import (
    CreateNamespaceApiRequest,
    NamespaceApiResponse,
    NamespaceSummaryApiResponse,
    UpdateNamespacePropertiesApiRequest,
)
from context.catalog.adapter.inbound.web.namespace.router import router

__all__ = [
    "CreateNamespaceApiRequest",
    "NamespaceApiResponse",
    "NamespaceSummaryApiResponse",
    "UpdateNamespacePropertiesApiRequest",
    "router",
]
