"""Test the application settings defaults, environment parsing and secret handling."""

from __future__ import annotations

import os

import pytest

from bootstrap.configs import AppSettings, Component, DatabaseBackend, TemporalSettings


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.startswith("GLAC_"):
            monkeypatch.delenv(name)


def test_defaults_follow_the_brief():
    """With no environment the settings use the documented component, backend and Temporal defaults."""
    settings = AppSettings()

    assert settings.component is Component.API
    assert settings.database_backend is DatabaseBackend.POSTGRES
    assert settings.temporal.address == "temporal-frontend.temporal.svc.cluster.local:7233"
    assert settings.temporal.namespace == "default"
    assert settings.catalog.uri == ("http://polaris.lakehouse-catalog.svc.cluster.local:8181/api/catalog")
    assert settings.catalog.management_uri == (
        "http://polaris.lakehouse-catalog.svc.cluster.local:8181/api/management/v1"
    )
    assert settings.catalog.scope == "PRINCIPAL_ROLE:ALL"
    assert settings.catalog.names == ["iceberg"]
    assert settings.catalog.s3_endpoint == ("http://rustfs.object-storage.svc.cluster.local:9000")
    assert settings.catalog.s3_access_key_id is None
    assert settings.catalog.s3_secret_access_key is None
    assert settings.kafka.bootstrap_servers == ("kafka-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092")
    assert settings.kafka.topic == "polaris-catalog-events"
    assert settings.spark.namespace == "lakehouse-maintenance-operations"
    assert settings.api.root_path == ""
    assert settings.admission_limit == 2
    assert settings.discovery_interval_seconds == 600


def test_nested_env_vars_are_parsed(monkeypatch: pytest.MonkeyPatch):
    """Nested environment variables override the component, database backend and SQLite path."""
    env = {
        "GLAC_COMPONENT": "worker",
        "GLAC_DATABASE_BACKEND": "sqlite",
        "GLAC_SQLITE__PATH": "/data/tm.db",
        "GLAC_POSTGRES__DB_URL": "postgresql+psycopg://u:pw@db:5432/tm",
        "GLAC_POSTGRES__POOL_SIZE": "9",
        "GLAC_TEMPORAL__ADDRESS": "temporal:7233",
        "GLAC_TEMPORAL__NAMESPACE": "tm",
        "GLAC_CATALOG__URI": "http://polaris:8181/api/catalog",
        "GLAC_CATALOG__MANAGEMENT_URI": "http://polaris:8181/api/management/v1",
        "GLAC_CATALOG__CREDENTIAL": "root:s3cr3t",
        "GLAC_CATALOG__NAMES": '["a","b"]',
        "GLAC_CATALOG__S3_ACCESS_KEY_ID": "AKID",
        "GLAC_CATALOG__S3_SECRET_ACCESS_KEY": "SK",
        "GLAC_KAFKA__BOOTSTRAP_SERVERS": "broker:9092",
        "GLAC_SPARK__IMAGE": "spark:1",
        "GLAC_SPARK__SIZE_S__EXECUTOR_INSTANCES": "3",
        "GLAC_CALLBACK_BASE_URL": "http://api:8000",
        "GLAC_ADMISSION_LIMIT": "4",
        "GLAC_DISCOVERY_INTERVAL_SECONDS": "60",
        "GLAC_API__ROOT_PATH": "/api",
    }
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    settings = AppSettings()

    assert settings.component is Component.WORKER
    assert settings.database_backend is DatabaseBackend.SQLITE
    assert settings.sqlite.path == "/data/tm.db"
    assert settings.postgres.db_url.get_secret_value() == ("postgresql+psycopg://u:pw@db:5432/tm")
    assert settings.postgres.pool_size == 9
    assert settings.temporal.address == "temporal:7233"
    assert settings.temporal.namespace == "tm"
    assert settings.catalog.uri == "http://polaris:8181/api/catalog"
    assert settings.catalog.management_uri == "http://polaris:8181/api/management/v1"
    assert settings.catalog.credential.get_secret_value() == "root:s3cr3t"
    assert settings.catalog.names == ["a", "b"]
    assert settings.catalog.s3_access_key_id is not None
    assert settings.catalog.s3_access_key_id.get_secret_value() == "AKID"
    assert settings.catalog.s3_secret_access_key is not None
    assert settings.catalog.s3_secret_access_key.get_secret_value() == "SK"
    assert settings.kafka.bootstrap_servers == "broker:9092"
    assert settings.spark.image == "spark:1"
    assert settings.spark.size_s.executor_instances == 3
    assert settings.callback_base_url == "http://api:8000"
    assert settings.admission_limit == 4
    assert settings.discovery_interval_seconds == 60
    assert settings.api.root_path == "/api"


def test_secrets_are_not_rendered(monkeypatch: pytest.MonkeyPatch):
    """Secret values do not appear in the rendered settings."""
    monkeypatch.setenv("GLAC_POSTGRES__DB_URL", "postgresql+psycopg://u:pw@db/tm")
    monkeypatch.setenv("GLAC_CATALOG__CREDENTIAL", "root:s3cr3t")

    rendered = repr(AppSettings())

    assert "pw@db" not in rendered
    assert "s3cr3t" not in rendered


def test_task_queue_is_not_configurable(monkeypatch: pytest.MonkeyPatch):
    """The Temporal task queue is fixed and offered by no setting."""
    monkeypatch.setenv("GLAC_TEMPORAL__TASK_QUEUE", "other")

    settings = AppSettings()

    assert "task_queue" not in TemporalSettings.model_fields
    assert not hasattr(settings.temporal, "task_queue")


def test_attempt_deadline_defaults_to_six_hours():
    """Without an environment each maintenance attempt may run six hours."""
    assert AppSettings().maintenance_attempt_deadline_seconds == 21600


def test_attempt_deadline_reads_env(monkeypatch: pytest.MonkeyPatch):
    """The attempt deadline is read from GLAC_MAINTENANCE_ATTEMPT_DEADLINE_SECONDS."""
    monkeypatch.setenv("GLAC_MAINTENANCE_ATTEMPT_DEADLINE_SECONDS", "120")

    assert AppSettings().maintenance_attempt_deadline_seconds == 120


def test_sizes_default_to_s_m_l():
    """The S, M and L sizes default to their driver and executor memory and one executor."""
    spark = AppSettings().spark
    assert (spark.size_s.driver_memory, spark.size_s.executor_memory, spark.size_s.executor_instances) == (
        "768m",
        "768m",
        1,
    )
    assert (spark.size_m.driver_memory, spark.size_m.executor_memory, spark.size_m.executor_instances) == (
        "1g",
        "1536m",
        1,
    )
    assert (spark.size_l.driver_memory, spark.size_l.executor_memory, spark.size_l.executor_instances) == (
        "1536m",
        "2g",
        1,
    )


def test_size_reads_env(monkeypatch: pytest.MonkeyPatch):
    """Each size's memory and executor count are read from the environment."""
    monkeypatch.setenv("GLAC_SPARK__SIZE_L__EXECUTOR_MEMORY", "3g")
    monkeypatch.setenv("GLAC_SPARK__SIZE_M__EXECUTOR_INSTANCES", "2")
    spark = AppSettings().spark
    assert spark.size_l.executor_memory == "3g"
    assert spark.size_l.driver_memory == "1536m"
    assert spark.size_m.executor_instances == 2


def test_compaction_defaults_pick_ten_partitions_and_hold_none_for_size():
    """Without an environment a run compacts ten partitions and only the quiet period holds one back."""
    compaction = AppSettings().compaction

    assert (compaction.partitions_per_run, compaction.min_partition_bytes) == (10, 0)
    assert (compaction.quiet_seconds, compaction.max_quiet_wait_seconds) == (120, 3600)
    assert (compaction.benefit_weight, compaction.cost_weight) == (0.7, 0.3)
    assert (compaction.benefit_reference_files, compaction.cost_reference_gb_hours) == (100, 1.0)
    assert compaction.default_throughput_bytes_per_hour == 2 * 1024**3
    assert compaction.min_throughput_sample_bytes == 64 * 1024**2
    assert (compaction.size_s_max_bytes, compaction.size_m_max_bytes) == (256 * 1024**2, 1024**3)


def test_compaction_reads_env(monkeypatch: pytest.MonkeyPatch):
    """Each compaction setting is read from GLAC_COMPACTION__<NAME>."""
    monkeypatch.setenv("GLAC_COMPACTION__PARTITIONS_PER_RUN", "3")
    monkeypatch.setenv("GLAC_COMPACTION__MIN_PARTITION_BYTES", "1048576")
    monkeypatch.setenv("GLAC_COMPACTION__QUIET_SECONDS", "30")
    monkeypatch.setenv("GLAC_COMPACTION__MAX_QUIET_WAIT_SECONDS", "600")
    monkeypatch.setenv("GLAC_COMPACTION__COST_WEIGHT", "0.5")
    monkeypatch.setenv("GLAC_COMPACTION__MIN_THROUGHPUT_SAMPLE_BYTES", "1024")

    compaction = AppSettings().compaction

    assert (compaction.partitions_per_run, compaction.min_partition_bytes) == (3, 1048576)
    assert (compaction.quiet_seconds, compaction.max_quiet_wait_seconds, compaction.cost_weight) == (30, 600, 0.5)
    assert compaction.min_throughput_sample_bytes == 1024


def test_scheduler_defaults_run_a_round_every_two_minutes_within_a_small_budget():
    """Without an environment a round runs every 120 s, grants up to 0.05 GB·h and keeps 500 rounds."""
    scheduler = AppSettings().scheduler

    assert (scheduler.round_seconds, scheduler.budget_gb_hours) == (120, 0.05)
    assert (scheduler.priority_weights.p0, scheduler.priority_weights.p1, scheduler.priority_weights.p2) == (
        4.0,
        2.0,
        1.0,
    )
    assert (scheduler.sla_seconds.p0, scheduler.sla_seconds.p1, scheduler.sla_seconds.p2) == (3600, 14400, 28800)
    assert (scheduler.grant_lease_seconds, scheduler.rounds_kept) == (600, 500)


def test_scheduler_reads_env(monkeypatch: pytest.MonkeyPatch):
    """Each scheduler setting is read from GLAC_SCHEDULER__<NAME>; a priority given alone keeps the others."""
    monkeypatch.setenv("GLAC_SCHEDULER__ROUND_SECONDS", "60")
    monkeypatch.setenv("GLAC_SCHEDULER__BUDGET_GB_HOURS", "0.2")
    monkeypatch.setenv("GLAC_SCHEDULER__PRIORITY_WEIGHTS__P0", "8")
    monkeypatch.setenv("GLAC_SCHEDULER__SLA_SECONDS__P2", "120")
    monkeypatch.setenv("GLAC_SCHEDULER__GRANT_LEASE_SECONDS", "900")
    monkeypatch.setenv("GLAC_SCHEDULER__ROUNDS_KEPT", "10")

    scheduler = AppSettings().scheduler

    assert (scheduler.round_seconds, scheduler.budget_gb_hours) == (60, 0.2)
    assert (scheduler.priority_weights.p0, scheduler.priority_weights.p1) == (8.0, 2.0)
    assert (scheduler.sla_seconds.p0, scheduler.sla_seconds.p2) == (3600, 120)
    assert (scheduler.grant_lease_seconds, scheduler.rounds_kept) == (900, 10)
