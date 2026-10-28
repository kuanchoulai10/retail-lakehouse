"""Define the Repositories bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.port.outbound.table_discovery_settings.table_discovery_settings_repo import (
        TableDiscoverySettingsRepo,
    )
    from application.port.outbound.table_discovery_rule.table_discovery_rules_repo import (
        TableDiscoveryRulesRepo,
    )
    from application.port.outbound.maintenance_run.maintenance_runs_repo import (
        MaintenanceRunsRepo,
    )
    from application.port.outbound.table.tables_repo import (
        TablesRepo,
    )
    from application.port.outbound.table_maintenance_preset.table_maintenance_presets_repo import (
        TableMaintenancePresetsRepo,
    )


@dataclass(frozen=True)
class Repositories:
    """Hold one repository per aggregate."""

    table_discovery_settings: TableDiscoverySettingsRepo
    table_discovery_rules: TableDiscoveryRulesRepo
    maintenance_runs: MaintenanceRunsRepo
    tables: TablesRepo
    table_maintenance_presets: TableMaintenancePresetsRepo
