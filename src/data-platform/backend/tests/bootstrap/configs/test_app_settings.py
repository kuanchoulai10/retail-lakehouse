"""Test the application settings defaults, environment parsing and secret handling."""

from __future__ import annotations

import os

import pytest

from bootstrap.configs import AppSettings, Component, DatabaseBackend, TemporalSettings
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_QUEUE_WAIT_LIMIT_SECONDS,
)
from context.table_maintenance.application.domain.model.table import DEFAULT_FAILURE_BACKOFF_CAP


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
    assert "admission_limit" not in AppSettings.model_fields
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


def test_queue_wait_limit_defaults_to_24_hours():
    """Without an environment each maintenance attempt may wait a day in its queue."""
    assert AppSettings().maintenance_queue_wait_limit_seconds == 86400


def test_queue_wait_limit_reads_env(monkeypatch: pytest.MonkeyPatch):
    """The queue wait limit is read from GLAC_MAINTENANCE_QUEUE_WAIT_LIMIT_SECONDS."""
    monkeypatch.setenv("GLAC_MAINTENANCE_QUEUE_WAIT_LIMIT_SECONDS", "600")

    assert AppSettings().maintenance_queue_wait_limit_seconds == 600


def test_queue_wait_limit_must_be_at_least_one_second(monkeypatch: pytest.MonkeyPatch):
    """An attempt may always wait at least a second, so zero is refused at start-up."""
    monkeypatch.setenv("GLAC_MAINTENANCE_QUEUE_WAIT_LIMIT_SECONDS", "0")

    with pytest.raises(ValueError, match="maintenance_queue_wait_limit_seconds"):
        AppSettings()


def test_max_attempts_defaults_to_three():
    """Without an environment each maintenance operation gets three attempts, as the workflow always did."""
    assert AppSettings().maintenance_max_attempts == 3


def test_max_attempts_reads_env(monkeypatch: pytest.MonkeyPatch):
    """The attempts per operation are read from GLAC_MAINTENANCE_MAX_ATTEMPTS."""
    monkeypatch.setenv("GLAC_MAINTENANCE_MAX_ATTEMPTS", "5")

    assert AppSettings().maintenance_max_attempts == 5


def test_max_attempts_must_be_at_least_one(monkeypatch: pytest.MonkeyPatch):
    """An operation always gets at least one attempt, so zero is refused at start-up."""
    monkeypatch.setenv("GLAC_MAINTENANCE_MAX_ATTEMPTS", "0")

    with pytest.raises(ValueError, match="maintenance_max_attempts"):
        AppSettings()


def test_failure_backoff_cap_defaults_to_24_hours():
    """Without an environment the doubling of a failing operation's cooldown stops at 24 hours."""
    assert AppSettings().maintenance_failure_backoff_cap_seconds == 86400


def test_failure_backoff_cap_reads_env(monkeypatch: pytest.MonkeyPatch):
    """The failure backoff cap is read from GLAC_MAINTENANCE_FAILURE_BACKOFF_CAP_SECONDS."""
    monkeypatch.setenv("GLAC_MAINTENANCE_FAILURE_BACKOFF_CAP_SECONDS", "3600")

    assert AppSettings().maintenance_failure_backoff_cap_seconds == 3600


def test_failure_backoff_cap_must_be_positive(monkeypatch: pytest.MonkeyPatch):
    """A cap of zero would erase every cooldown, so it is refused at start-up."""
    monkeypatch.setenv("GLAC_MAINTENANCE_FAILURE_BACKOFF_CAP_SECONDS", "0")

    with pytest.raises(ValueError, match="maintenance_failure_backoff_cap_seconds"):
        AppSettings()


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


def test_settings_hold_no_round_scheduling_or_candidate_selection_group():
    """Compaction rounds and candidate selection are gone, so neither has settings to read."""
    assert {"scheduler", "compaction"}.isdisjoint(AppSettings.model_fields)


def test_attempt_and_backoff_defaults_match_the_domain_defaults():
    """The settings repeat the contexts' named defaults (configs may not import a context), so they must agree."""
    settings = AppSettings()

    assert settings.maintenance_max_attempts == DEFAULT_MAX_ATTEMPTS
    assert settings.maintenance_queue_wait_limit_seconds == DEFAULT_QUEUE_WAIT_LIMIT_SECONDS
    assert settings.maintenance_failure_backoff_cap_seconds == DEFAULT_FAILURE_BACKOFF_CAP.total_seconds()


def test_volcano_defaults_name_the_chart_queues_and_classes():
    """Without an environment the jobs go to the chart's queues and priority classes."""
    volcano = AppSettings().spark.volcano

    assert (volcano.queue, volcano.urgent_queue, volcano.priority_class_prefix) == (
        "table-maintenance",
        "table-maintenance-urgent",
        "table-maintenance",
    )


def test_volcano_reads_env(monkeypatch: pytest.MonkeyPatch):
    """The queues and the class prefix are read from GLAC_SPARK__VOLCANO__<NAME>."""
    monkeypatch.setenv("GLAC_SPARK__VOLCANO__QUEUE", "q")
    monkeypatch.setenv("GLAC_SPARK__VOLCANO__URGENT_QUEUE", "uq")
    monkeypatch.setenv("GLAC_SPARK__VOLCANO__PRIORITY_CLASS_PREFIX", "pc")

    volcano = AppSettings().spark.volcano

    assert (volcano.queue, volcano.urgent_queue, volcano.priority_class_prefix) == ("q", "uq", "pc")
