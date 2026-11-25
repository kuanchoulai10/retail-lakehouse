"""Define the AppSettings configuration model."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from bootstrap.configs.catalog_settings import CatalogSettings
from bootstrap.configs.component import Component
from bootstrap.configs.database_backend import DatabaseBackend
from bootstrap.configs.http_settings import HttpSettings
from bootstrap.configs.kafka_settings import KafkaSettings
from bootstrap.configs.metrics_settings import MetricsSettings
from bootstrap.configs.postgres_settings import PostgresSettings
from bootstrap.configs.spark_settings import SparkSettings
from bootstrap.configs.sqlite_settings import SqliteSettings
from bootstrap.configs.temporal_settings import TemporalSettings


class AppSettings(BaseSettings):
    """Root application settings, read from ``GLAC_`` environment variables.

    Nested fields use ``__``, for example ``GLAC_TEMPORAL__ADDRESS``.
    """

    model_config = SettingsConfigDict(
        env_prefix="GLAC_",
        env_nested_delimiter="__",
    )

    component: Component = Component.API
    log_level: str = "INFO"
    database_backend: DatabaseBackend = DatabaseBackend.POSTGRES
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    sqlite: SqliteSettings = Field(default_factory=SqliteSettings)
    temporal: TemporalSettings = Field(default_factory=TemporalSettings)
    catalog: CatalogSettings = Field(default_factory=CatalogSettings)
    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)
    spark: SparkSettings = Field(default_factory=SparkSettings)
    api: HttpSettings = Field(default_factory=HttpSettings)
    callback_base_url: str = "http://table-maintenance-api.lakehouse-control-plane.svc.cluster.local:8000"
    discovery_interval_seconds: int = 600
    maintenance_attempt_deadline_seconds: int = 21600
    maintenance_max_attempts: int = Field(default=3, ge=1)
    maintenance_queue_wait_limit_seconds: int = Field(default=86400, ge=1)
    maintenance_failure_backoff_cap_seconds: int = Field(default=86400, ge=1)
    maintenance_rewrite_data_files_cooldown_seconds: int = Field(default=3600, ge=0)
    maintenance_rewrite_manifests_cooldown_seconds: int = Field(default=21600, ge=0)
    maintenance_expire_snapshots_cooldown_seconds: int = Field(default=21600, ge=0)
    maintenance_remove_orphan_files_interval_seconds: int = Field(default=604800, ge=1)
    maintenance_compaction_partitions_per_job: int = Field(default=10, ge=1, le=1000)
    maintenance_compaction_quiet_seconds: int = Field(default=120, ge=0)
    maintenance_compaction_max_quiet_wait_seconds: int = Field(default=3600, ge=0)
