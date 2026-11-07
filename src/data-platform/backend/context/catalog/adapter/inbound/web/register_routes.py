"""Define the register_routes function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.adapter.inbound.web.error_handlers import register_error_handlers

if TYPE_CHECKING:
    from fastapi import FastAPI

    from context.catalog.adapter.inbound.web.shared import WebUseCases


def register_routes(app: FastAPI, use_cases: WebUseCases) -> None:
    """Mount the catalog routes and error handlers on the app."""
    app.state.catalog_use_cases = use_cases
    register_error_handlers(app)
