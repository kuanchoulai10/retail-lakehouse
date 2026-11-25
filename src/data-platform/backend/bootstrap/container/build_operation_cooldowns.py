"""Provide the build_operation_cooldowns function."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import OperationCooldowns

if TYPE_CHECKING:
    from bootstrap.configs import MaintenanceSettings


def build_operation_cooldowns(maintenance: MaintenanceSettings) -> OperationCooldowns:
    """Return the platform's cooldown of each maintenance operation and its failure backoff cap."""
    return OperationCooldowns(
        rewrite_data_files=timedelta(seconds=maintenance.rewrite_data_files_cooldown_seconds),
        rewrite_manifests=timedelta(seconds=maintenance.rewrite_manifests_cooldown_seconds),
        expire_snapshots=timedelta(seconds=maintenance.expire_snapshots_cooldown_seconds),
        remove_orphan_files=timedelta(seconds=maintenance.remove_orphan_files_interval_seconds),
        failure_backoff_cap=timedelta(seconds=maintenance.failure_backoff_cap_seconds),
    )
