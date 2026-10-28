"""Inbound web adapter."""

from __future__ import annotations

# The child routers import web_use_cases and WebUseCases while this package
# initialises, so those modules are imported before create_app.
from adapter.inbound.web.web_use_cases import WebUseCases
from adapter.inbound.web.use_cases_dependency import web_use_cases
from adapter.inbound.web.error_handlers import register_error_handlers
from adapter.inbound.web.create_app import create_app

__all__ = [
    "WebUseCases",
    "create_app",
    "register_error_handlers",
    "web_use_cases",
]
