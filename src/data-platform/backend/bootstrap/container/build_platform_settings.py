"""Provide the build_platform_settings function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    PlatformComputeSize,
    PlatformPriority,
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
    scheduler = settings.scheduler
    compaction = settings.compaction
    return PlatformSettings(
        attempt_deadline_seconds=settings.maintenance_attempt_deadline_seconds,
        max_attempts=settings.maintenance_max_attempts,
        compute_sizes=(
            _compute_size(ComputeSize.S, settings.spark.size_s),
            _compute_size(ComputeSize.M, settings.spark.size_m),
            _compute_size(ComputeSize.L, settings.spark.size_l),
        ),
        round_seconds=scheduler.round_seconds,
        budget_gb_hours=scheduler.budget_gb_hours,
        priorities=(
            PlatformPriority(priority="P0", weight=scheduler.priority_weights.p0, sla_seconds=scheduler.sla_seconds.p0),
            PlatformPriority(priority="P1", weight=scheduler.priority_weights.p1, sla_seconds=scheduler.sla_seconds.p1),
            PlatformPriority(priority="P2", weight=scheduler.priority_weights.p2, sla_seconds=scheduler.sla_seconds.p2),
        ),
        grant_lease_seconds=scheduler.grant_lease_seconds,
        partitions_per_run=compaction.partitions_per_run,
        quiet_seconds=compaction.quiet_seconds,
        max_quiet_wait_seconds=compaction.max_quiet_wait_seconds,
        min_partition_bytes=compaction.min_partition_bytes,
        failure_backoff_cap_seconds=settings.maintenance_failure_backoff_cap_seconds,
        discovery_interval_seconds=settings.discovery_interval_seconds,
    )


def _compute_size(size: ComputeSize, resources: SparkSizeSettings) -> PlatformComputeSize:
    return PlatformComputeSize(
        size=size,
        driver_memory=resources.driver_memory,
        executor_memory=resources.executor_memory,
        executor_instances=resources.executor_instances,
    )
