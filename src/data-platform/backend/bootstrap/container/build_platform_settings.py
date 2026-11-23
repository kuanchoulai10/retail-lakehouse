"""Provide the build_platform_settings function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    PlatformComputeSize,
    PlatformSettings,
)

if TYPE_CHECKING:
    from bootstrap.configs import AppSettings, SparkSizeSettings


def build_platform_settings(settings: AppSettings) -> PlatformSettings:
    """Return the platform settings the console may show, chosen field by field from the application settings.

    This is the whitelist: a setting is listed only because it is named here. The settings
    object is never dumped, so no secret, address or credential can reach the page by
    being added to it.
    """
    return PlatformSettings(
        attempt_deadline_seconds=settings.maintenance_attempt_deadline_seconds,
        max_attempts=settings.maintenance_max_attempts,
        queue_wait_limit_seconds=settings.maintenance_queue_wait_limit_seconds,
        compute_sizes=(
            _compute_size(ComputeSize.S, settings.spark.size_s),
            _compute_size(ComputeSize.M, settings.spark.size_m),
            _compute_size(ComputeSize.L, settings.spark.size_l),
        ),
        rewrite_data_files_cooldown_seconds=settings.maintenance_rewrite_data_files_cooldown_seconds,
        rewrite_manifests_cooldown_seconds=settings.maintenance_rewrite_manifests_cooldown_seconds,
        expire_snapshots_cooldown_seconds=settings.maintenance_expire_snapshots_cooldown_seconds,
        remove_orphan_files_interval_seconds=settings.maintenance_remove_orphan_files_interval_seconds,
        failure_backoff_cap_seconds=settings.maintenance_failure_backoff_cap_seconds,
        discovery_interval_seconds=settings.discovery_interval_seconds,
        compaction_partitions_per_job=settings.maintenance_compaction_partitions_per_job,
        compaction_quiet_seconds=settings.maintenance_compaction_quiet_seconds,
        compaction_max_quiet_wait_seconds=settings.maintenance_compaction_max_quiet_wait_seconds,
    )


def _compute_size(size: ComputeSize, resources: SparkSizeSettings) -> PlatformComputeSize:
    return PlatformComputeSize(
        size=size,
        coordinator_memory=resources.driver_memory,
        worker_memory=resources.executor_memory,
        worker_count=resources.executor_instances,
    )
