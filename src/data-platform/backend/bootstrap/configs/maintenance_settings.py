"""Define the MaintenanceSettings configuration model."""

from __future__ import annotations

from pydantic import Field

from bootstrap.configs.settings_block import SettingsBlock


class MaintenanceSettings(SettingsBlock):
    """How maintenance attempts run, retry and wait, and how a scheduled compaction picks its partitions.

    The API's platform settings page shows these values, so the API and the worker must be given the same.
    """

    attempt_deadline_seconds: int = 21600
    max_attempts: int = Field(default=3, ge=1)
    queue_wait_limit_seconds: int = Field(default=86400, ge=1)
    failure_backoff_cap_seconds: int = Field(default=86400, ge=1)
    rewrite_data_files_cooldown_seconds: int = Field(default=3600, ge=0)
    rewrite_manifests_cooldown_seconds: int = Field(default=21600, ge=0)
    expire_snapshots_cooldown_seconds: int = Field(default=21600, ge=0)
    remove_orphan_files_interval_seconds: int = Field(default=604800, ge=1)
    compaction_partitions_per_job: int = Field(default=10, ge=1, le=1000)
    compaction_quiet_seconds: int = Field(default=120, ge=0)
    compaction_max_quiet_wait_seconds: int = Field(default=3600, ge=0)
