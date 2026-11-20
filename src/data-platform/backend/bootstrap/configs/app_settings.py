"""Define the AppSettings configuration model."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from bootstrap.configs.api_settings import ApiSettings
from bootstrap.configs.catalog_settings import CatalogSettings
from bootstrap.configs.compaction_settings import CompactionSettings
from bootstrap.configs.component import Component
from bootstrap.configs.database_backend import DatabaseBackend
from bootstrap.configs.kafka_settings import KafkaSettings
from bootstrap.configs.postgres_settings import PostgresSettings
from bootstrap.configs.scheduler_settings import SchedulerSettings
from bootstrap.configs.spark_settings import SparkSettings
from bootstrap.configs.sqlite_settings import SqliteSettings
from bootstrap.configs.temporal_settings import TemporalSettings


class AppSettings(BaseSettings):
    """Root application settings, read from ``GLAC_`` environment variables.

    Nested fields use ``__``, for example ``GLAC_TEMPORAL__ADDRESS``; list fields
    take JSON, for example ``GLAC_CATALOG__NAMES='["iceberg"]'``.
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
    spark: SparkSettings = Field(default_factory=SparkSettings)
    compaction: CompactionSettings = Field(default_factory=CompactionSettings)
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)
    callback_base_url: str = "http://table-maintenance-api.lakehouse-control-plane.svc.cluster.local:8000"
    discovery_interval_seconds: int = 600
    maintenance_attempt_deadline_seconds: int = 21600
    maintenance_max_attempts: int = Field(default=3, ge=1)
    maintenance_failure_backoff_cap_seconds: int = Field(default=86400, ge=1)
