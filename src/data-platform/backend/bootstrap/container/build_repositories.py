"""Provide the build_repositories function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from adapter.outbound.table_discovery_settings.sql import TableDiscoverySettingsSqlRepo
from adapter.outbound.table_discovery_rule.sql import TableDiscoveryRulesSqlRepo
from adapter.outbound.table_maintenance_run.sql import TableMaintenanceRunsSqlRepo
from adapter.outbound.table.sql import TablesSqlRepo
from adapter.outbound.table_maintenance_preset.sql import TableMaintenancePresetsSqlRepo
from bootstrap.container.repositories import Repositories

if TYPE_CHECKING:
    from sqlalchemy import Engine


def build_repositories(engine: Engine) -> Repositories:
    """Build the SQL repositories on one engine."""
    return Repositories(
        table_discovery_settings=TableDiscoverySettingsSqlRepo(engine),
        table_discovery_rules=TableDiscoveryRulesSqlRepo(engine),
        table_maintenance_runs=TableMaintenanceRunsSqlRepo(engine),
        tables=TablesSqlRepo(engine),
        table_maintenance_presets=TableMaintenancePresetsSqlRepo(engine),
    )
