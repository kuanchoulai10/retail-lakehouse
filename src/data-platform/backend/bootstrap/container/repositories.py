"""Define the Repositories bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.port.outbound.table_discovery_settings import (
        TableDiscoverySettingsRepo,
    )
    from application.port.outbound.table_discovery_rule import TableDiscoveryRulesRepo
    from application.port.outbound.table_maintenance_run import TableMaintenanceRunsRepo
    from application.port.outbound.table import TablesRepo
    from application.port.outbound.table_maintenance_preset import (
        TableMaintenancePresetsRepo,
    )


@dataclass(frozen=True)
class Repositories:
    """Hold one repository per aggregate."""

    table_discovery_settings: TableDiscoverySettingsRepo
    table_discovery_rules: TableDiscoveryRulesRepo
    table_maintenance_runs: TableMaintenanceRunsRepo
    tables: TablesRepo
    table_maintenance_presets: TableMaintenancePresetsRepo
