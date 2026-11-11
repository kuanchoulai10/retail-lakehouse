"""Define the WebUseCases bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.table import (
        GetTableHealthUseCase,
        GetTableStorageUseCase,
        GetTableUseCase,
        ListTableCommitsUseCase,
        ListTablesUseCase,
        TriggerTableMaintenanceUseCase,
        TriggerTableReconciliationUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_discovery_rules import (
        GetTableDiscoveryRulesUseCase,
        ListCoveredCatalogsUseCase,
        PreviewTableDiscoveryRulesUseCase,
        ReplaceTableDiscoveryRulesUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_maintenance_run import (
        GetTableMaintenanceRunUseCase,
        ListTableMaintenanceRunsUseCase,
        ProcessTableMaintenanceCallbackUseCase,
    )
    from context.table_maintenance.application.port.inbound.table_reconciliation import (
        ListTableReconciliationsUseCase,
    )


@dataclass(frozen=True)
class WebUseCases:
    """Hold every use case the web API calls; the composition root builds it."""

    get_table_discovery_rules: GetTableDiscoveryRulesUseCase
    replace_table_discovery_rules: ReplaceTableDiscoveryRulesUseCase
    preview_table_discovery_rules: PreviewTableDiscoveryRulesUseCase
    list_covered_catalogs: ListCoveredCatalogsUseCase
    list_tables: ListTablesUseCase
    get_table: GetTableUseCase
    get_table_health: GetTableHealthUseCase
    get_table_storage: GetTableStorageUseCase
    list_table_commits: ListTableCommitsUseCase
    trigger_table_maintenance: TriggerTableMaintenanceUseCase
    trigger_table_reconciliation: TriggerTableReconciliationUseCase
    list_table_maintenance_runs: ListTableMaintenanceRunsUseCase
    get_table_maintenance_run: GetTableMaintenanceRunUseCase
    process_table_maintenance_callback: ProcessTableMaintenanceCallbackUseCase
    list_table_reconciliations: ListTableReconciliationsUseCase
