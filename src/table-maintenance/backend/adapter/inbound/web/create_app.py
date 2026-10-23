"""Define the create_app function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from adapter.inbound.web.discovery.router import router as discovery_router
from adapter.inbound.web.discovery_rule.router import router as discovery_rule_router
from adapter.inbound.web.error_handlers import register_error_handlers
from adapter.inbound.web.maintenance_run.router import router as maintenance_run_router
from adapter.inbound.web.managed_table.router import router as managed_table_router
from adapter.inbound.web.policy_template.router import router as policy_template_router
from fastapi import FastAPI

if TYPE_CHECKING:
    from adapter.inbound.web.web_use_cases import WebUseCases

_API_PREFIX = "/v1"


def create_app(use_cases: WebUseCases) -> FastAPI:
    """Build the control plane API around the given use cases."""
    app = FastAPI(title="Table Maintenance Control Plane")
    app.state.use_cases = use_cases
    register_error_handlers(app)
    for router in (
        discovery_rule_router,
        discovery_router,
        policy_template_router,
        managed_table_router,
        maintenance_run_router,
    ):
        app.include_router(router, prefix=_API_PREFIX)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app
