"""Define the web_use_cases dependency."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from fastapi import Request  # noqa: TC002 - FastAPI resolves the annotation at runtime

if TYPE_CHECKING:
    from adapter.inbound.web.web_use_cases import WebUseCases


def web_use_cases(request: Request) -> WebUseCases:
    """Return the use cases that create_app stored on the application."""
    return cast("WebUseCases", request.app.state.use_cases)
