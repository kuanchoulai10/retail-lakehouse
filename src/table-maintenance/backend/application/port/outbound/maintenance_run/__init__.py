"""Outbound ports for the maintenance_run group."""

from application.port.outbound.maintenance_run.maintenance_runs_repo import (
    MaintenanceRunsRepo,
)

__all__ = ["MaintenanceRunsRepo"]
