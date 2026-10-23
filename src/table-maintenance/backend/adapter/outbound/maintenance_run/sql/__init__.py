"""SQL-backed MaintenanceRun repository components."""

from adapter.outbound.maintenance_run.sql.maintenance_runs_sql_repo import (
    MaintenanceRunsSqlRepo,
)

__all__ = ["MaintenanceRunsSqlRepo"]
