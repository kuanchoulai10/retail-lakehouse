"""Define the Repositories bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.catalog_discovery import (
        CatalogDiscoveriesRepo,
    )
    from context.table_maintenance.application.port.outbound.compaction_candidate import (
        CompactionCandidatesRepo,
    )
    from context.table_maintenance.application.port.outbound.compaction_round import (
        CompactionRoundsRepo,
    )
    from context.table_maintenance.application.port.outbound.table import TablesRepo
    from context.table_maintenance.application.port.outbound.table_discovery_rules import (
        TableDiscoveryRulesRepo,
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
    """Hold one repository per aggregate."""

    table_discovery_rules: TableDiscoveryRulesRepo
    table_maintenance_runs: TableMaintenanceRunsRepo
    tables: TablesRepo
    table_maintenance_policies: TableMaintenancePoliciesRepo
    table_maintenance_policy_attachments: TableMaintenancePolicyAttachmentsRepo
    table_reconciliations: TableReconciliationsRepo
    compaction_candidates: CompactionCandidatesRepo
    compaction_rounds: CompactionRoundsRepo
    catalog_discoveries: CatalogDiscoveriesRepo
