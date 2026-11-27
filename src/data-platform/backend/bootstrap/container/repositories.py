"""Define the Repositories bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.catalog import CatalogsRepo
    from context.table_maintenance.application.port.outbound.catalog_discovery import (
        CatalogDiscoveriesRepo,
    )
    from context.table_maintenance.application.port.outbound.namespace import NamespacesRepo
    from context.table_maintenance.application.port.outbound.shared import PolicyPlacementsStore
    from context.table_maintenance.application.port.outbound.table import TableMetricsStore, TablesRepo
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
        TableMaintenancePolicyAttachmentsRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        TableMaintenanceRunsRepo,
    )
    from context.table_maintenance.application.port.outbound.table_reconciliation import (
        TableReconciliationsRepo,
    )


@dataclass(frozen=True)
class Repositories:
    """Hold one repository per aggregate, the table metrics store and the policy placements store."""

    table_discovery_policies: TableDiscoveryPoliciesRepo
    table_maintenance_runs: TableMaintenanceRunsRepo
    tables: TablesRepo
    table_maintenance_policies: TableMaintenancePoliciesRepo
    table_maintenance_policy_attachments: TableMaintenancePolicyAttachmentsRepo
    table_reconciliations: TableReconciliationsRepo
    catalog_discoveries: CatalogDiscoveriesRepo
    catalogs: CatalogsRepo
    namespaces: NamespacesRepo
    table_metrics: TableMetricsStore
    policy_placements: PolicyPlacementsStore
