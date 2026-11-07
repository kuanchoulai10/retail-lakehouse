"""Define the register_routes function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.adapter.inbound.web.catalog import router as catalog_router
from context.catalog.adapter.inbound.web.error_handlers import register_error_handlers
from context.catalog.adapter.inbound.web.namespace import router as namespace_router

if TYPE_CHECKING:
    from fastapi import FastAPI

    from context.catalog.adapter.inbound.web.shared import WebUseCases

_API_PREFIX = "/v1"


def register_routes(app: FastAPI, use_cases: WebUseCases) -> None:
    """Mount the catalog routes and error handlers on the app."""
    app.state.catalog_use_cases = use_cases
    register_error_handlers(app)
    for router in (catalog_router, namespace_router):
        app.include_router(router, prefix=_API_PREFIX)
