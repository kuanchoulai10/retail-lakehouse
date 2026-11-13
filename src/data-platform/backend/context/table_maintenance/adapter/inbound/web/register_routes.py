"""Define the register_routes function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.adapter.inbound.web.compaction_candidate import (
    router as compaction_candidate_router,
)
from context.table_maintenance.adapter.inbound.web.compaction_round import (
    router as compaction_round_router,
)
from context.table_maintenance.adapter.inbound.web.error_handlers import (
    register_error_handlers,
)
from context.table_maintenance.adapter.inbound.web.table import router as table_router
from context.table_maintenance.adapter.inbound.web.table_discovery_rules import (
    router as table_discovery_rules_router,
)
from context.table_maintenance.adapter.inbound.web.table_maintenance_policy import (
    router as table_maintenance_policy_router,
)
from context.table_maintenance.adapter.inbound.web.table_maintenance_policy_attachment import (
    router as table_maintenance_policy_attachment_router,
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
        table_discovery_rules_router,
        table_maintenance_policy_router,
        table_maintenance_policy_attachment_router,
        table_router,
        table_maintenance_run_router,
        table_reconciliation_router,
        compaction_candidate_router,
        compaction_round_router,
    ):
        app.include_router(router, prefix=_API_PREFIX)
