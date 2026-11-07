"""Inbound web adapter."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.create_app import create_app
from context.table_maintenance.adapter.inbound.web.error_handlers import (
    register_error_handlers,
)

__all__ = [
    "create_app",
    "register_error_handlers",
]
