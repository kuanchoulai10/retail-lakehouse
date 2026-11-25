"""Test the worker's settings defaults, environment parsing and secret handling, and the blocks it shares."""

from __future__ import annotations

import os

import pytest
from pydantic import ValidationError

from bootstrap.configs import (
    ApiSettings,
    CatalogSettings,
    DatabaseBackend,
    EventConsumerSettings,
    TemporalSettings,
    WorkerSettings,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_QUEUE_WAIT_LIMIT_SECONDS,
)
from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table import (
    DEFAULT_FAILURE_BACKOFF_CAP,
    OperationCooldowns,
    PartitionSelectionSettings,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.startswith("GLAC_"):
            monkeypatch.delenv(name)


def test_defaults_follow_the_brief():
    """With no environment the settings use the documented backend, Temporal and catalog defaults."""
    settings = WorkerSettings()

    assert settings.database.backend is DatabaseBackend.POSTGRES
    assert settings.temporal.address == "temporal-frontend.temporal.svc.cluster.local:7233"
    assert settings.temporal.namespace == "default"
    assert settings.catalog.uri == ("http://polaris.lakehouse-catalog.svc.cluster.local:8181/api/catalog")
    assert settings.catalog.management_uri == (
        "http://polaris.lakehouse-catalog.svc.cluster.local:8181/api/management/v1"
    )
    assert settings.catalog.scope == "PRINCIPAL_ROLE:ALL"
    assert settings.catalog.s3_endpoint == ("http://rustfs.object-storage.svc.cluster.local:9000")
    assert settings.catalog.s3_access_key_id is None
    assert settings.catalog.s3_secret_access_key is None
    assert settings.spark.namespace == "lakehouse-maintenance-operations"
    assert "admission_limit" not in WorkerSettings.model_fields
    assert settings.discovery.interval_seconds == 600


def test_catalog_settings_have_no_names():
    """The catalogs to scan follow the discovery policy attachments, so no catalog list is configured."""
    assert "names" not in CatalogSettings.model_fields


def test_nested_env_vars_are_parsed(monkeypatch: pytest.MonkeyPatch):
    """Nested environment variables override the database, Temporal, catalog, Spark and callback settings."""
    env = {
        "GLAC_DATABASE__BACKEND": "sqlite",
        "GLAC_DATABASE__SQLITE__PATH": "/data/tm.db",
        "GLAC_DATABASE__POSTGRES__DB_URL": "postgresql+psycopg://u:pw@db:5432/tm",
        "GLAC_DATABASE__POSTGRES__POOL_SIZE": "9",
        "GLAC_TEMPORAL__ADDRESS": "temporal:7233",
        "GLAC_TEMPORAL__NAMESPACE": "tm",
        "GLAC_CATALOG__URI": "http://polaris:8181/api/catalog",
        "GLAC_CATALOG__MANAGEMENT_URI": "http://polaris:8181/api/management/v1",
        "GLAC_CATALOG__CREDENTIAL": "root:s3cr3t",
        "GLAC_CATALOG__S3_ACCESS_KEY_ID": "AKID",
        "GLAC_CATALOG__S3_SECRET_ACCESS_KEY": "SK",
        "GLAC_SPARK__IMAGE": "spark:1",
        "GLAC_SPARK__SIZE_S__EXECUTOR_INSTANCES": "3",
        "GLAC_CALLBACK_BASE_URL": "http://api:8000",
        "GLAC_DISCOVERY__INTERVAL_SECONDS": "60",
    }
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    settings = WorkerSettings()

    assert settings.database.backend is DatabaseBackend.SQLITE
    assert settings.database.sqlite.path == "/data/tm.db"
    assert settings.database.postgres.db_url.get_secret_value() == ("postgresql+psycopg://u:pw@db:5432/tm")
    assert settings.database.postgres.pool_size == 9
    assert settings.temporal.address == "temporal:7233"
    assert settings.temporal.namespace == "tm"
    assert settings.catalog.uri == "http://polaris:8181/api/catalog"
    assert settings.catalog.management_uri == "http://polaris:8181/api/management/v1"
    assert settings.catalog.credential.get_secret_value() == "root:s3cr3t"
    assert settings.catalog.s3_access_key_id is not None
    assert settings.catalog.s3_access_key_id.get_secret_value() == "AKID"
    assert settings.catalog.s3_secret_access_key is not None
    assert settings.catalog.s3_secret_access_key.get_secret_value() == "SK"
    assert settings.spark.image == "spark:1"
    assert settings.spark.size_s.executor_instances == 3
    assert settings.callback_base_url == "http://api:8000"
    assert settings.discovery.interval_seconds == 60


def test_the_api_adds_the_http_settings(monkeypatch: pytest.MonkeyPatch):
    """Only the API has an HTTP root path; it defaults to the root and reads GLAC_HTTP__ROOT_PATH."""
    assert ApiSettings().http.root_path == ""
    monkeypatch.setenv("GLAC_HTTP__ROOT_PATH", "/api")

    assert ApiSettings().http.root_path == "/api"


def test_the_event_consumer_reads_kafka(monkeypatch: pytest.MonkeyPatch):
    """Only the event consumer has Kafka settings, with the cluster defaults."""
    settings = EventConsumerSettings()

    assert settings.kafka.bootstrap_servers == ("kafka-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092")
    assert settings.kafka.topic == "polaris-catalog-events"
    monkeypatch.setenv("GLAC_KAFKA__BOOTSTRAP_SERVERS", "broker:9092")

    assert EventConsumerSettings().kafka.bootstrap_servers == "broker:9092"


def test_secrets_are_not_rendered(monkeypatch: pytest.MonkeyPatch):
    """Secret values do not appear in the rendered settings."""
    monkeypatch.setenv("GLAC_DATABASE__POSTGRES__DB_URL", "postgresql+psycopg://u:pw@db/tm")
    monkeypatch.setenv("GLAC_CATALOG__CREDENTIAL", "root:s3cr3t")

    rendered = repr(WorkerSettings())

    assert "pw@db" not in rendered
    assert "s3cr3t" not in rendered


def test_task_queue_is_not_configurable(monkeypatch: pytest.MonkeyPatch):
    """The Temporal task queue is fixed and offered by no setting; naming one is refused."""
    monkeypatch.setenv("GLAC_TEMPORAL__TASK_QUEUE", "other")

    assert "task_queue" not in TemporalSettings.model_fields
    with pytest.raises(ValidationError):
        WorkerSettings()


def test_attempt_deadline_defaults_to_six_hours():
    """Without an environment each maintenance attempt may run six hours."""
    assert WorkerSettings().maintenance.attempt_deadline_seconds == 21600


def test_attempt_deadline_reads_env(monkeypatch: pytest.MonkeyPatch):
    """The attempt deadline is read from GLAC_MAINTENANCE__ATTEMPT_DEADLINE_SECONDS."""
    monkeypatch.setenv("GLAC_MAINTENANCE__ATTEMPT_DEADLINE_SECONDS", "120")

    assert WorkerSettings().maintenance.attempt_deadline_seconds == 120


def test_queue_wait_limit_defaults_to_24_hours():
    """Without an environment each maintenance attempt may wait a day in its queue."""
    assert WorkerSettings().maintenance.queue_wait_limit_seconds == 86400


def test_queue_wait_limit_reads_env(monkeypatch: pytest.MonkeyPatch):
    """The queue wait limit is read from GLAC_MAINTENANCE__QUEUE_WAIT_LIMIT_SECONDS."""
    monkeypatch.setenv("GLAC_MAINTENANCE__QUEUE_WAIT_LIMIT_SECONDS", "600")

    assert WorkerSettings().maintenance.queue_wait_limit_seconds == 600


def test_queue_wait_limit_must_be_at_least_one_second(monkeypatch: pytest.MonkeyPatch):
    """An attempt may always wait at least a second, so zero is refused at start-up."""
    monkeypatch.setenv("GLAC_MAINTENANCE__QUEUE_WAIT_LIMIT_SECONDS", "0")

    with pytest.raises(ValueError, match=r"maintenance\.queue_wait_limit_seconds"):
        WorkerSettings()


def test_max_attempts_defaults_to_three():
    """Without an environment each maintenance operation gets three attempts, as the workflow always did."""
    assert WorkerSettings().maintenance.max_attempts == 3


def test_max_attempts_reads_env(monkeypatch: pytest.MonkeyPatch):
    """The attempts per operation are read from GLAC_MAINTENANCE__MAX_ATTEMPTS."""
    monkeypatch.setenv("GLAC_MAINTENANCE__MAX_ATTEMPTS", "5")

    assert WorkerSettings().maintenance.max_attempts == 5


def test_max_attempts_must_be_at_least_one(monkeypatch: pytest.MonkeyPatch):
    """An operation always gets at least one attempt, so zero is refused at start-up."""
    monkeypatch.setenv("GLAC_MAINTENANCE__MAX_ATTEMPTS", "0")

    with pytest.raises(ValueError, match=r"maintenance\.max_attempts"):
        WorkerSettings()


def test_failure_backoff_cap_defaults_to_24_hours():
    """Without an environment the doubling of a failing operation's cooldown stops at 24 hours."""
    assert WorkerSettings().maintenance.failure_backoff_cap_seconds == 86400


def test_failure_backoff_cap_reads_env(monkeypatch: pytest.MonkeyPatch):
    """The failure backoff cap is read from GLAC_MAINTENANCE__FAILURE_BACKOFF_CAP_SECONDS."""
    monkeypatch.setenv("GLAC_MAINTENANCE__FAILURE_BACKOFF_CAP_SECONDS", "3600")

    assert WorkerSettings().maintenance.failure_backoff_cap_seconds == 3600


def test_failure_backoff_cap_must_be_positive(monkeypatch: pytest.MonkeyPatch):
    """A cap of zero would erase every cooldown, so it is refused at start-up."""
    monkeypatch.setenv("GLAC_MAINTENANCE__FAILURE_BACKOFF_CAP_SECONDS", "0")

    with pytest.raises(ValueError, match=r"maintenance\.failure_backoff_cap_seconds"):
        WorkerSettings()


def test_cooldowns_default_to_the_platform_defaults():
    """Without an environment the cooldowns are 1 hour, 6 hours and 6 hours, and orphan files are removed weekly."""
    settings = WorkerSettings()

    assert settings.maintenance.rewrite_data_files_cooldown_seconds == 3600
    assert settings.maintenance.rewrite_manifests_cooldown_seconds == 21600
    assert settings.maintenance.expire_snapshots_cooldown_seconds == 21600
    assert settings.maintenance.remove_orphan_files_interval_seconds == 604800


def test_app_settings_read_the_cooldown_env(monkeypatch: pytest.MonkeyPatch):
    """Each cooldown and the orphan file interval are read from their GLAC_MAINTENANCE__* name."""
    monkeypatch.setenv("GLAC_MAINTENANCE__REWRITE_DATA_FILES_COOLDOWN_SECONDS", "60")
    monkeypatch.setenv("GLAC_MAINTENANCE__REWRITE_MANIFESTS_COOLDOWN_SECONDS", "120")
    monkeypatch.setenv("GLAC_MAINTENANCE__EXPIRE_SNAPSHOTS_COOLDOWN_SECONDS", "180")
    monkeypatch.setenv("GLAC_MAINTENANCE__REMOVE_ORPHAN_FILES_INTERVAL_SECONDS", "240")

    settings = WorkerSettings()

    assert settings.maintenance.rewrite_data_files_cooldown_seconds == 60
    assert settings.maintenance.rewrite_manifests_cooldown_seconds == 120
    assert settings.maintenance.expire_snapshots_cooldown_seconds == 180
    assert settings.maintenance.remove_orphan_files_interval_seconds == 240


@pytest.mark.parametrize(
    "name",
    [
        "REWRITE_DATA_FILES_COOLDOWN_SECONDS",
        "REWRITE_MANIFESTS_COOLDOWN_SECONDS",
        "EXPIRE_SNAPSHOTS_COOLDOWN_SECONDS",
    ],
)
def test_negative_cooldown_is_refused(monkeypatch: pytest.MonkeyPatch, name: str):
    """A cooldown may be zero but never negative."""
    monkeypatch.setenv(f"GLAC_MAINTENANCE__{name}", "-1")

    with pytest.raises(ValueError, match=rf"maintenance\.{name.lower()}"):
        WorkerSettings()


def test_zero_cooldown_is_allowed(monkeypatch: pytest.MonkeyPatch):
    """A cooldown of zero means the operation may run at every plan."""
    monkeypatch.setenv("GLAC_MAINTENANCE__REWRITE_DATA_FILES_COOLDOWN_SECONDS", "0")

    assert WorkerSettings().maintenance.rewrite_data_files_cooldown_seconds == 0


def test_orphan_file_interval_must_be_positive(monkeypatch: pytest.MonkeyPatch):
    """Orphan files are due on this interval, so zero is refused at start-up."""
    monkeypatch.setenv("GLAC_MAINTENANCE__REMOVE_ORPHAN_FILES_INTERVAL_SECONDS", "0")

    with pytest.raises(ValueError, match=r"maintenance\.remove_orphan_files_interval_seconds"):
        WorkerSettings()


def test_cooldown_defaults_match_the_domain_defaults():
    """The settings repeat the platform default cooldowns (configs may not import a context), so they must agree."""
    settings = WorkerSettings()
    default = OperationCooldowns.platform_default()

    assert [
        settings.maintenance.rewrite_data_files_cooldown_seconds,
        settings.maintenance.rewrite_manifests_cooldown_seconds,
        settings.maintenance.expire_snapshots_cooldown_seconds,
        settings.maintenance.remove_orphan_files_interval_seconds,
    ] == [default.for_operation(op).total_seconds() for op in MaintenanceOperation.ordered()]


def test_sizes_default_to_s_m_l():
    """The S, M and L sizes default to their driver and executor memory and one executor."""
    spark = WorkerSettings().spark
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
    spark = WorkerSettings().spark
    assert spark.size_l.executor_memory == "3g"
    assert spark.size_l.driver_memory == "1536m"
    assert spark.size_m.executor_instances == 2


def test_app_settings_read_the_partition_selection_env(monkeypatch: pytest.MonkeyPatch):
    """The partitions per job, the quiet period and the longest wait are read from their GLAC_MAINTENANCE__* name."""
    monkeypatch.setenv("GLAC_MAINTENANCE__COMPACTION_PARTITIONS_PER_JOB", "4")
    monkeypatch.setenv("GLAC_MAINTENANCE__COMPACTION_QUIET_SECONDS", "0")
    monkeypatch.setenv("GLAC_MAINTENANCE__COMPACTION_MAX_QUIET_WAIT_SECONDS", "600")

    settings = WorkerSettings()

    assert (
        settings.maintenance.compaction_partitions_per_job,
        settings.maintenance.compaction_quiet_seconds,
        settings.maintenance.compaction_max_quiet_wait_seconds,
    ) == (4, 0, 600)


def test_the_partition_selection_bounds_are_accepted(monkeypatch: pytest.MonkeyPatch):
    """The cap accepts 1 and 1000, and the longest wait accepts 0 (nothing waits)."""
    monkeypatch.setenv("GLAC_MAINTENANCE__COMPACTION_MAX_QUIET_WAIT_SECONDS", "0")
    for value in (1, 1000):
        monkeypatch.setenv("GLAC_MAINTENANCE__COMPACTION_PARTITIONS_PER_JOB", str(value))
        settings = WorkerSettings()
        assert (
            settings.maintenance.compaction_partitions_per_job,
            settings.maintenance.compaction_max_quiet_wait_seconds,
        ) == (value, 0)


@pytest.mark.parametrize("value", ["0", "1001"])
def test_partitions_per_job_out_of_range_is_refused(monkeypatch: pytest.MonkeyPatch, value: str):
    """One job compacts at least one partition and at most a thousand, which bounds the size of its where."""
    monkeypatch.setenv("GLAC_MAINTENANCE__COMPACTION_PARTITIONS_PER_JOB", value)

    with pytest.raises(ValueError, match=r"maintenance\.compaction_partitions_per_job"):
        WorkerSettings()


@pytest.mark.parametrize("name", ["QUIET_SECONDS", "MAX_QUIET_WAIT_SECONDS"])
def test_negative_quiet_is_refused(monkeypatch: pytest.MonkeyPatch, name: str):
    """The quiet period and the longest wait may be zero but never negative."""
    monkeypatch.setenv(f"GLAC_MAINTENANCE__COMPACTION_{name}", "-1")

    with pytest.raises(ValueError, match=rf"maintenance\.compaction_{name.lower()}"):
        WorkerSettings()


def test_partition_selection_defaults_match_the_domain_defaults():
    """The settings repeat the platform default selection (configs may not import a context), so they must agree."""
    settings, default = WorkerSettings(), PartitionSelectionSettings.platform_default()

    assert (
        settings.maintenance.compaction_partitions_per_job,
        settings.maintenance.compaction_quiet_seconds,
        settings.maintenance.compaction_max_quiet_wait_seconds,
    ) == (default.partitions_per_job, default.quiet_period.total_seconds(), default.max_quiet_wait.total_seconds())


def test_settings_hold_no_round_scheduling_or_candidate_selection_group():
    """Compaction rounds and candidate selection are gone, so neither has settings to read."""
    assert {"scheduler", "compaction"}.isdisjoint(WorkerSettings.model_fields)


def test_attempt_and_backoff_defaults_match_the_domain_defaults():
    """The settings repeat the contexts' named defaults (configs may not import a context), so they must agree."""
    settings = WorkerSettings()

    assert settings.maintenance.max_attempts == DEFAULT_MAX_ATTEMPTS
    assert settings.maintenance.queue_wait_limit_seconds == DEFAULT_QUEUE_WAIT_LIMIT_SECONDS
    assert settings.maintenance.failure_backoff_cap_seconds == DEFAULT_FAILURE_BACKOFF_CAP.total_seconds()


def test_volcano_defaults_name_the_chart_queues_and_classes():
    """Without an environment the jobs go to the chart's queues and priority classes."""
    volcano = WorkerSettings().spark.volcano

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

    volcano = WorkerSettings().spark.volcano

    assert (volcano.queue, volcano.urgent_queue, volcano.priority_class_prefix) == ("q", "uq", "pc")


def test_metrics_settings_default_to_the_cluster_prometheus():
    """Without an environment the trends are read from the table metrics Prometheus, within ten seconds."""
    settings = WorkerSettings()

    assert settings.metrics.prometheus_url == "http://table-metrics-prometheus.table-metrics.svc.cluster.local:9090"
    assert settings.metrics.query_timeout_seconds == 10.0


def test_metrics_settings_read_env(monkeypatch: pytest.MonkeyPatch):
    """The Prometheus url and the query timeout come from GLAC_METRICS__* variables."""
    monkeypatch.setenv("GLAC_METRICS__PROMETHEUS_URL", "http://prom:9090")
    monkeypatch.setenv("GLAC_METRICS__QUERY_TIMEOUT_SECONDS", "2.5")

    settings = WorkerSettings()

    assert settings.metrics.prometheus_url == "http://prom:9090"
    assert settings.metrics.query_timeout_seconds == 2.5
