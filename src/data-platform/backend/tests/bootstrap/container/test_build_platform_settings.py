"""Test that the platform settings are built from an explicit whitelist of the application settings."""

from __future__ import annotations

import json

from bootstrap.container import build_platform_settings
from context.table_maintenance.application.domain.model.shared import ComputeSize, PlatformSettings
from tests.bootstrap.container.container_support import sqlite_settings

WHITELIST = {
    "attempt_deadline_seconds",
    "max_attempts",
    "compute_sizes",
    "round_seconds",
    "budget_gb_hours",
    "priorities",
    "grant_lease_seconds",
    "partitions_per_run",
    "quiet_seconds",
    "max_quiet_wait_seconds",
    "min_partition_bytes",
    "failure_backoff_cap_seconds",
    "discovery_interval_seconds",
}
SECRETS = ("s3cr3t-pass", "AKIDSECRET", "SKSECRET", "root:cat4log", "kafka-user")


def test_the_platform_settings_hold_exactly_the_whitelisted_fields():
    """A new field on the platform settings is a deliberate change: this list must grow with it."""
    assert set(PlatformSettings.model_fields) == WHITELIST


def test_defaults_are_the_values_the_platform_ran_with_before_they_had_names():
    """With no environment the values are the ones that used to be hard-coded or defaulted."""
    settings = build_platform_settings(sqlite_settings())

    assert (settings.attempt_deadline_seconds, settings.max_attempts) == (21600, 3)
    assert settings.failure_backoff_cap_seconds == 86400
    assert settings.discovery_interval_seconds == 600
    assert (settings.round_seconds, settings.budget_gb_hours, settings.grant_lease_seconds) == (120, 0.05, 600)
    assert [(p.priority, p.weight, p.sla_seconds) for p in settings.priorities] == [
        ("P0", 4.0, 3600),
        ("P1", 2.0, 14400),
        ("P2", 1.0, 28800),
    ]
    assert (settings.partitions_per_run, settings.quiet_seconds, settings.max_quiet_wait_seconds) == (10, 120, 3600)
    assert settings.min_partition_bytes == 0
    assert [(s.size, s.driver_memory, s.executor_memory, s.executor_instances) for s in settings.compute_sizes] == [
        (ComputeSize.S, "768m", "768m", 1),
        (ComputeSize.M, "1g", "1536m", 1),
        (ComputeSize.L, "1536m", "2g", 1),
    ]


def test_values_follow_the_application_settings():
    """What the deployment sets is what is shown, for every listed setting."""
    settings = build_platform_settings(
        sqlite_settings(
            maintenance_attempt_deadline_seconds=900,
            maintenance_max_attempts=5,
            maintenance_failure_backoff_cap_seconds=7200,
            discovery_interval_seconds=60,
            scheduler={
                "round_seconds": 30,
                "budget_gb_hours": 0.4,
                "priority_weights": {"p0": 8.0},
                "sla_seconds": {"p1": 60},
                "grant_lease_seconds": 90,
            },
            compaction={
                "partitions_per_run": 3,
                "quiet_seconds": 5,
                "max_quiet_wait_seconds": 50,
                "min_partition_bytes": 1024,
            },
            spark={"size_m": {"executor_instances": 3}},
        )
    )

    assert (settings.attempt_deadline_seconds, settings.max_attempts) == (900, 5)
    assert (settings.failure_backoff_cap_seconds, settings.discovery_interval_seconds) == (7200, 60)
    assert (settings.round_seconds, settings.budget_gb_hours, settings.grant_lease_seconds) == (30, 0.4, 90)
    assert (settings.priorities[0].weight, settings.priorities[1].sla_seconds) == (8.0, 60)
    assert (settings.partitions_per_run, settings.quiet_seconds) == (3, 5)
    assert (settings.max_quiet_wait_seconds, settings.min_partition_bytes) == (50, 1024)
    assert settings.compute_sizes[1].executor_instances == 3


def test_no_secret_of_the_deployment_reaches_the_platform_settings():
    """Catalog, object storage, database and Kafka secrets never appear in what is built from the settings."""
    settings = sqlite_settings(
        catalog={
            "credential": "root:cat4log",
            "s3_access_key_id": "AKIDSECRET",
            "s3_secret_access_key": "SKSECRET",
            "uri": "http://kafka-user:s3cr3t-pass@polaris:8181/api/catalog",
        },
        postgres={"db_url": "postgresql+psycopg://tm:s3cr3t-pass@db:5432/tm"},
        kafka={"bootstrap_servers": "kafka-user:s3cr3t-pass@broker:9092"},
    )

    rendered = json.dumps(build_platform_settings(settings).to_primitives()) + repr(build_platform_settings(settings))

    assert not [secret for secret in SECRETS if secret in rendered]
