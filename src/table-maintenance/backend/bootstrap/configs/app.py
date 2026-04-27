"""Define the AppSettings configuration model."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from bootstrap.configs.component import Component
from bootstrap.configs.database_backend import DatabaseBackend
from bootstrap.configs.submit_job_run_gateway_adapter import SubmitJobRunGatewayAdapter
from bootstrap.configs.job_runs_repo_adapter import JobRunsRepoAdapter
from bootstrap.configs.jobs_repo_adapter import JobsRepoAdapter
from bootstrap.configs.k8s_settings import K8sSettings
from bootstrap.configs.messaging_settings import MessagingSettings
from bootstrap.configs.postgres_settings import PostgresSettings
from bootstrap.configs.scheduler_settings import SchedulerSettings
from bootstrap.configs.sqlite_settings import SqliteSettings


class AppSettings(BaseSettings):
    """Root application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="GLAC_",
        env_nested_delimiter="__",
    )

    component: Component = Component.API

    jobs_repo_adapter: JobsRepoAdapter = JobsRepoAdapter.IN_MEMORY
    job_runs_repo_adapter: JobRunsRepoAdapter = JobRunsRepoAdapter.IN_MEMORY
    submit_job_run_gateway_adapter: SubmitJobRunGatewayAdapter = (
        SubmitJobRunGatewayAdapter.IN_MEMORY
    )
    database_backend: DatabaseBackend = DatabaseBackend.SQLITE
    k8s: K8sSettings = Field(default_factory=K8sSettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    sqlite: SqliteSettings = Field(default_factory=SqliteSettings)
    iceberg_catalog_uri: str = "http://polaris:8181/api/catalog"
    iceberg_catalog_name: str = "iceberg"
    iceberg_catalog_credential: str = ""
    iceberg_catalog_warehouse: str = ""
    iceberg_catalog_scope: str = ""

    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    messaging: MessagingSettings = Field(default_factory=MessagingSettings)
