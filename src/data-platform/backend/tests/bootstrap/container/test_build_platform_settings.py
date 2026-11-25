"""Test that the platform settings are built from an explicit whitelist of the application settings."""

from __future__ import annotations

import json

from bootstrap.container import build_platform_settings
from context.table_maintenance.application.domain.model.shared import ComputeSize, PlatformSettings
from tests.bootstrap.container.container_support import sqlite_settings

WHITELIST = {
    "attempt_deadline_seconds",
    "max_attempts",
    "queue_wait_limit_seconds",
    "compute_sizes",
    "rewrite_data_files_cooldown_seconds",
    "rewrite_manifests_cooldown_seconds",
    "expire_snapshots_cooldown_seconds",
    "remove_orphan_files_interval_seconds",
    "failure_backoff_cap_seconds",
    "discovery_interval_seconds",
    "compaction_partitions_per_job",
    "compaction_quiet_seconds",
    "compaction_max_quiet_wait_seconds",
}
SECRETS = ("s3cr3t-pass", "AKIDSECRET", "SKSECRET", "root:cat4log", "kafka-user")


def test_the_platform_settings_hold_exactly_the_whitelisted_fields():
    """A new field on the platform settings is a deliberate change: this list must grow with it."""
    assert set(PlatformSettings.model_fields) == WHITELIST


def test_defaults_are_the_values_the_platform_ran_with_before_they_had_names():
    """With no environment the values are the ones that used to be hard-coded or defaulted."""
    settings = build_platform_settings(sqlite_settings())

    assert (settings.attempt_deadline_seconds, settings.max_attempts) == (21600, 3)
    assert settings.queue_wait_limit_seconds == 86400
    assert settings.failure_backoff_cap_seconds == 86400
    assert (
        settings.rewrite_data_files_cooldown_seconds,
        settings.rewrite_manifests_cooldown_seconds,
        settings.expire_snapshots_cooldown_seconds,
        settings.remove_orphan_files_interval_seconds,
    ) == (3600, 21600, 21600, 604800)
    assert settings.discovery_interval_seconds == 600
    assert (
        settings.compaction_partitions_per_job,
        settings.compaction_quiet_seconds,
        settings.compaction_max_quiet_wait_seconds,
    ) == (10, 120, 3600)
    assert [(s.size, s.coordinator_memory, s.worker_memory, s.worker_count) for s in settings.compute_sizes] == [
        (ComputeSize.S, "768m", "768m", 1),
        (ComputeSize.M, "1g", "1536m", 1),
        (ComputeSize.L, "1536m", "2g", 1),
    ]


def test_values_follow_the_application_settings():
    """What the deployment sets is what is shown, for every listed setting."""
    settings = build_platform_settings(
        sqlite_settings(
            spark={"size_m": {"executor_instances": 3}},
            maintenance={
                "attempt_deadline_seconds": 900,
                "max_attempts": 5,
                "queue_wait_limit_seconds": 1800,
                "failure_backoff_cap_seconds": 7200,
                "rewrite_data_files_cooldown_seconds": 60,
                "rewrite_manifests_cooldown_seconds": 120,
                "expire_snapshots_cooldown_seconds": 180,
                "remove_orphan_files_interval_seconds": 240,
            },
            discovery={"interval_seconds": 60},
        )
    )

    assert (settings.attempt_deadline_seconds, settings.max_attempts) == (900, 5)
    assert settings.queue_wait_limit_seconds == 1800
    assert (settings.failure_backoff_cap_seconds, settings.discovery_interval_seconds) == (7200, 60)
    assert (
        settings.rewrite_data_files_cooldown_seconds,
        settings.rewrite_manifests_cooldown_seconds,
        settings.expire_snapshots_cooldown_seconds,
        settings.remove_orphan_files_interval_seconds,
    ) == (60, 120, 180, 240)
    assert settings.compute_sizes[1].worker_count == 3


def test_build_platform_settings_copies_the_partition_selection():
    """The three partition selection settings are shown as the deployment sets them."""
    settings = build_platform_settings(
        sqlite_settings(
            maintenance={
                "compaction_partitions_per_job": 4,
                "compaction_quiet_seconds": 0,
                "compaction_max_quiet_wait_seconds": 600,
            }
        )
    )

    assert (
        settings.compaction_partitions_per_job,
        settings.compaction_quiet_seconds,
        settings.compaction_max_quiet_wait_seconds,
    ) == (4, 0, 600)


def test_no_secret_of_the_deployment_reaches_the_platform_settings():
    """Catalog, object storage, database and metrics secrets never appear in what is built from the settings."""
    settings = sqlite_settings(
        catalog={
            "credential": "root:cat4log",
            "s3_access_key_id": "AKIDSECRET",
            "s3_secret_access_key": "SKSECRET",
            "uri": "http://kafka-user:s3cr3t-pass@polaris:8181/api/catalog",
        },
        database={
            "backend": "sqlite",
            "sqlite": {"path": ":memory:"},
            "postgres": {"db_url": "postgresql+psycopg://tm:s3cr3t-pass@db:5432/tm"},
        },
        metrics={"prometheus_url": "http://kafka-user:s3cr3t-pass@prometheus:9090"},
    )

    rendered = json.dumps(build_platform_settings(settings).to_primitives()) + repr(build_platform_settings(settings))

    assert not [secret for secret in SECRETS if secret in rendered]


def test_platform_settings_come_from_the_maintenance_block():
    """The page shows the maintenance block's values, read from the settings the API is given."""
    settings = build_platform_settings(sqlite_settings(maintenance={"compaction_quiet_seconds": 61}))

    assert settings.compaction_quiet_seconds == 61
