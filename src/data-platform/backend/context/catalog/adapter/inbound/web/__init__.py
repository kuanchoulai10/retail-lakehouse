"""Inbound web adapter of the catalog context."""

from __future__ import annotations

from context.catalog.adapter.inbound.web.error_handlers import register_error_handlers
from context.catalog.adapter.inbound.web.register_routes import register_routes

__all__ = [
    "register_error_handlers",
    "register_routes",
]
