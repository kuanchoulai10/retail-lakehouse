"""Provide the build_partition_selection_settings function."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import PartitionSelectionSettings

if TYPE_CHECKING:
    from bootstrap.configs import MaintenanceSettings


def build_partition_selection_settings(maintenance: MaintenanceSettings) -> PartitionSelectionSettings:
    """Return how a scheduled compaction chooses the partitions of one job: its cap, quiet period and longest wait."""
    return PartitionSelectionSettings(
        partitions_per_job=maintenance.compaction_partitions_per_job,
        quiet_period=timedelta(seconds=maintenance.compaction_quiet_seconds),
        max_quiet_wait=timedelta(seconds=maintenance.compaction_max_quiet_wait_seconds),
    )
