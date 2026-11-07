"""Web adapter for the generic table group."""

from __future__ import annotations

from context.catalog.adapter.inbound.web.generic_table.dto import (
    CreateGenericTableApiRequest,
    GenericTableApiResponse,
    GenericTableIdentifierApiResponse,
)
from context.catalog.adapter.inbound.web.generic_table.router import router

__all__ = [
    "CreateGenericTableApiRequest",
    "GenericTableApiResponse",
    "GenericTableIdentifierApiResponse",
    "router",
]
