"""Inbound web adapter."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.error_handlers import (
    register_error_handlers,
)
from context.table_maintenance.adapter.inbound.web.register_routes import register_routes

__all__ = [
    "register_routes",
    "register_error_handlers",
]
