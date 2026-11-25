"""Test that the operation cooldowns are built from the application settings."""

from __future__ import annotations

from datetime import timedelta

from bootstrap.configs import MaintenanceSettings
from bootstrap.container import build_operation_cooldowns
from context.table_maintenance.application.domain.model.table import OperationCooldowns


def test_defaults_are_the_platform_default_cooldowns():
    """With no environment the cooldowns are the domain's platform default."""
    assert build_operation_cooldowns(MaintenanceSettings()) == OperationCooldowns.platform_default()


def test_cooldowns_follow_the_application_settings():
    """Each cooldown, the orphan file interval and the failure backoff cap are the ones the settings say."""
    cooldowns = build_operation_cooldowns(
        MaintenanceSettings.model_validate(
            {
                "rewrite_data_files_cooldown_seconds": 60,
                "rewrite_manifests_cooldown_seconds": 120,
                "expire_snapshots_cooldown_seconds": 180,
                "remove_orphan_files_interval_seconds": 240,
                "failure_backoff_cap_seconds": 7200,
            }
        )
    )

    assert cooldowns == OperationCooldowns(
        rewrite_data_files=timedelta(seconds=60),
        rewrite_manifests=timedelta(seconds=120),
        expire_snapshots=timedelta(seconds=180),
        remove_orphan_files=timedelta(seconds=240),
        failure_backoff_cap=timedelta(hours=2),
    )
