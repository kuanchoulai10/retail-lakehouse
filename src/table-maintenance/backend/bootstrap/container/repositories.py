"""Define the Repositories bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.port.outbound.discovery.discovery_settings_repo import (
        DiscoverySettingsRepo,
    )
    from application.port.outbound.discovery_rule.discovery_rules_repo import (
        DiscoveryRulesRepo,
    )
    from application.port.outbound.maintenance_run.maintenance_runs_repo import (
        MaintenanceRunsRepo,
    )
    from application.port.outbound.managed_table.managed_tables_repo import (
        ManagedTablesRepo,
    )
    from application.port.outbound.table_maintenance_preset.table_maintenance_presets_repo import (
        TableMaintenancePresetsRepo,
    )


@dataclass(frozen=True)
class Repositories:
    """Hold one repository per aggregate."""

    discovery_settings: DiscoverySettingsRepo
    discovery_rules: DiscoveryRulesRepo
    maintenance_runs: MaintenanceRunsRepo
    managed_tables: ManagedTablesRepo
    table_maintenance_presets: TableMaintenancePresetsRepo
