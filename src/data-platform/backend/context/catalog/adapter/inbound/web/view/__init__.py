"""Web adapter for the view group."""

from __future__ import annotations

from context.catalog.adapter.inbound.web.view.dto import (
    CreateViewApiRequest,
    ViewApiResponse,
    ViewIdentifierApiResponse,
    ViewVersionApiResponse,
)
from context.catalog.adapter.inbound.web.view.router import router

__all__ = [
    "CreateViewApiRequest",
    "ViewApiResponse",
    "ViewIdentifierApiResponse",
    "ViewVersionApiResponse",
    "router",
]
