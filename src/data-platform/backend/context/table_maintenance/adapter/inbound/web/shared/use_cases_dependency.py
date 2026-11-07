"""Define the use_cases_dependency FastAPI dependency."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from fastapi import Request  # noqa: TC002 - FastAPI resolves the annotation at runtime

if TYPE_CHECKING:
    from context.table_maintenance.adapter.inbound.web.shared.web_use_cases import (
        WebUseCases,
    )


def use_cases_dependency(request: Request) -> WebUseCases:
    """Return the use cases that register_routes stored on the application."""
    return cast("WebUseCases", request.app.state.table_maintenance_use_cases)
