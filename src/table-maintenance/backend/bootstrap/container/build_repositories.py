"""Provide the build_repositories function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from adapter.outbound.discovery.sql.discovery_settings_sql_repo import (
    DiscoverySettingsSqlRepo,
)
from adapter.outbound.discovery_rule.sql.discovery_rules_sql_repo import (
    DiscoveryRulesSqlRepo,
)
from adapter.outbound.maintenance_run.sql.maintenance_runs_sql_repo import (
    MaintenanceRunsSqlRepo,
)
from adapter.outbound.managed_table.sql.managed_tables_sql_repo import (
    ManagedTablesSqlRepo,
)
from adapter.outbound.policy_template.sql.policy_templates_sql_repo import (
    PolicyTemplatesSqlRepo,
)
from bootstrap.container.repositories import Repositories

if TYPE_CHECKING:
    from sqlalchemy import Engine


def build_repositories(engine: Engine) -> Repositories:
    """Build the SQL repositories on one engine."""
    return Repositories(
        discovery_settings=DiscoverySettingsSqlRepo(engine),
        discovery_rules=DiscoveryRulesSqlRepo(engine),
        maintenance_runs=MaintenanceRunsSqlRepo(engine),
        managed_tables=ManagedTablesSqlRepo(engine),
        policy_templates=PolicyTemplatesSqlRepo(engine),
    )
