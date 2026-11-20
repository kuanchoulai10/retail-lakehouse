"""Provide the build_repositories function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bootstrap.container.repositories import Repositories
from context.table_maintenance.adapter.outbound.catalog_discovery.sql import (
    CatalogDiscoveriesSqlRepo,
)
from context.table_maintenance.adapter.outbound.table.sql import TableMetricsSqlStore, TablesSqlRepo
from context.table_maintenance.adapter.outbound.table_discovery_rules.sql import (
    TableDiscoveryRulesSqlRepo,
)
from context.table_maintenance.adapter.outbound.table_maintenance_policy.sql import (
    TableMaintenancePoliciesSqlRepo,
)
from context.table_maintenance.adapter.outbound.table_maintenance_policy_attachment.sql import (
    TableMaintenancePolicyAttachmentsSqlRepo,
)
from context.table_maintenance.adapter.outbound.table_maintenance_run.sql import (
    TableMaintenanceRunsSqlRepo,
)
from context.table_maintenance.adapter.outbound.table_reconciliation.sql import (
    TableReconciliationsSqlRepo,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine


def build_repositories(engine: Engine) -> Repositories:
    """Build the SQL repositories on one engine."""
    return Repositories(
        table_discovery_rules=TableDiscoveryRulesSqlRepo(engine),
        table_maintenance_runs=TableMaintenanceRunsSqlRepo(engine),
        tables=TablesSqlRepo(engine),
        table_maintenance_policies=TableMaintenancePoliciesSqlRepo(engine),
        table_maintenance_policy_attachments=TableMaintenancePolicyAttachmentsSqlRepo(engine),
        table_reconciliations=TableReconciliationsSqlRepo(engine),
        catalog_discoveries=CatalogDiscoveriesSqlRepo(engine),
        table_metrics=TableMetricsSqlStore(engine),
    )
