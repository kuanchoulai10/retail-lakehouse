"""Provide the create_api_app function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI

if TYPE_CHECKING:
    from collections.abc import Callable


def create_api_app(*registrations: Callable[[FastAPI], None]) -> FastAPI:
    """Build the API app with a health check, then let each context register its routes."""
    app = FastAPI(title="Data Platform API")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    for register in registrations:
        register(app)
    return app
