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
        "GLAC_SPARK__EXECUTOR_INSTANCES": "3",
        "GLAC_CALLBACK_BASE_URL": "http://api:8000",
        "GLAC_ADMISSION_LIMIT": "4",
        "GLAC_DISCOVERY_INTERVAL_SECONDS": "60",
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
    assert settings.spark.executor_instances == 3
    assert settings.callback_base_url == "http://api:8000"
    assert settings.admission_limit == 4
    assert settings.discovery_interval_seconds == 60


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
