"""Define the register_routes function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.adapter.inbound.web.error_handlers import (
    register_error_handlers,
)
from context.table_maintenance.adapter.inbound.web.table import router as table_router
from context.table_maintenance.adapter.inbound.web.table_discovery_rule import (
    router as table_discovery_rule_router,
)
from context.table_maintenance.adapter.inbound.web.table_discovery_settings import (
    router as discovery_router,
)
from context.table_maintenance.adapter.inbound.web.table_maintenance_preset import (
    router as table_maintenance_preset_router,
)
from context.table_maintenance.adapter.inbound.web.table_maintenance_run import (
    router as table_maintenance_run_router,
)
from context.table_maintenance.adapter.inbound.web.table_reconciliation import (
    router as table_reconciliation_router,
)

if TYPE_CHECKING:
    from fastapi import FastAPI

    from context.table_maintenance.adapter.inbound.web.shared import WebUseCases

_API_PREFIX = "/v1"


def register_routes(app: FastAPI, use_cases: WebUseCases) -> None:
    """Mount the table maintenance routes and error handlers on the app."""
    app.state.table_maintenance_use_cases = use_cases
    register_error_handlers(app)
    for router in (
        table_discovery_rule_router,
        discovery_router,
        table_maintenance_preset_router,
        table_router,
        table_maintenance_run_router,
        table_reconciliation_router,
    ):
        app.include_router(router, prefix=_API_PREFIX)
