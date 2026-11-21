"""Define the plan_service_on_fakes helper."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.service.table import PlanTableMaintenanceService
from tests.context.table_maintenance.fakes.in_memory_table_metrics_store import InMemoryTableMetricsStore

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table import PartitionSelectionSettings
    from context.table_maintenance.application.port.inbound.table import PlanTableMaintenanceUseCase
    from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
        ResolveApplicableTableMaintenancePolicyUseCase,
    )
    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetadataGateway,
        TableMetricsStore,
        TablesRepo,
    )


def plan_service_on_fakes(
    tables_repo: TablesRepo,
    catalog: ReadTableMetadataGateway,
    resolve_applicable_policy: ResolveApplicableTableMaintenancePolicyUseCase,
    metrics_store: TableMetricsStore | None = None,
    *,
    partition_selection: PartitionSelectionSettings | None = None,
) -> PlanTableMaintenanceUseCase:
    """Return the plan service on the given fakes, with an empty in-memory metrics store when none is given.

    The partition selection is passed only when one is given, so the service keeps its own default otherwise.
    """
    store = InMemoryTableMetricsStore() if metrics_store is None else metrics_store
    if partition_selection is None:
        return PlanTableMaintenanceService(tables_repo, catalog, resolve_applicable_policy, metrics_store=store)
    return PlanTableMaintenanceService(
        tables_repo, catalog, resolve_applicable_policy, metrics_store=store, partition_selection=partition_selection
    )
