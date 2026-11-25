"""Test that the partition selection settings are built from the application settings."""

from __future__ import annotations

from datetime import timedelta

from bootstrap.configs import MaintenanceSettings
from bootstrap.container import build_partition_selection_settings
from context.table_maintenance.application.domain.model.table import PartitionSelectionSettings


def test_defaults_are_the_platform_default_selection():
    """With no environment the selection is the domain's platform default."""
    assert build_partition_selection_settings(MaintenanceSettings()) == PartitionSelectionSettings.platform_default()


def test_build_partition_selection_settings():
    """The cap, the quiet period and the longest wait are the ones the settings say."""
    settings = MaintenanceSettings.model_validate(
        {"compaction_partitions_per_job": 4, "compaction_quiet_seconds": 0, "compaction_max_quiet_wait_seconds": 600}
    )

    assert build_partition_selection_settings(settings) == PartitionSelectionSettings(
        partitions_per_job=4, quiet_period=timedelta(0), max_quiet_wait=timedelta(seconds=600)
    )
