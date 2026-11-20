"""Define the plan_service_on_fakes helper."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.service.table import PlanTableMaintenanceService

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.table import PlanTableMaintenanceUseCase
    from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
        ResolveApplicableTableMaintenancePolicyUseCase,
    )
    from context.table_maintenance.application.port.outbound.table import ReadTableMetadataGateway, TablesRepo


def plan_service_on_fakes(
    tables_repo: TablesRepo,
    catalog: ReadTableMetadataGateway,
    resolve_applicable_policy: ResolveApplicableTableMaintenancePolicyUseCase,
) -> PlanTableMaintenanceUseCase:
    """Return the plan service on the given fakes."""
    return PlanTableMaintenanceService(tables_repo, catalog, resolve_applicable_policy)
