"""Provide the create_api_app function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi.routing import APIRoute


def _operation_id(route: APIRoute) -> str:
    """Name each operation after its route, which the console's generated client uses for its hook names."""
    return route.name


def create_api_app(*registrations: Callable[[FastAPI], None], root_path: str = "") -> FastAPI:
    """Build the API app with a health check, then let each context register its routes.

    ``root_path`` is the public prefix a proxy strips before forwarding (``/api`` on
    the platform gateway). It moves the docs' OpenAPI URL and the OpenAPI ``servers``
    entry; requests that arrive without the prefix still route.
    """
    app = FastAPI(title="Data Platform API", generate_unique_id_function=_operation_id, root_path=root_path)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    for register in registrations:
        register(app)
    return app
