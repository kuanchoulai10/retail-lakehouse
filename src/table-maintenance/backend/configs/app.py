"""Define the AppSettings configuration model."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from configs.database_backend import DatabaseBackend
from configs.job_run_executor_adapter import JobRunExecutorAdapter
from configs.job_runs_repo_adapter import JobRunsRepoAdapter
from configs.jobs_repo_adapter import JobsRepoAdapter
from configs.k8s_settings import K8sSettings
from configs.postgres_settings import PostgresSettings
from configs.sqlite_settings import SqliteSettings


class AppSettings(BaseSettings):
    """Root application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="BACKEND_",
        env_nested_delimiter="__",
    )

    jobs_repo_adapter: JobsRepoAdapter = JobsRepoAdapter.IN_MEMORY
    job_runs_repo_adapter: JobRunsRepoAdapter = JobRunsRepoAdapter.IN_MEMORY
    job_run_executor_adapter: JobRunExecutorAdapter = JobRunExecutorAdapter.IN_MEMORY
    database_backend: DatabaseBackend = DatabaseBackend.SQLITE
    k8s: K8sSettings = Field(default_factory=K8sSettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    sqlite: SqliteSettings = Field(default_factory=SqliteSettings)
    iceberg_catalog_uri: str = "http://polaris:8181/api/catalog"
    iceberg_catalog_name: str = "iceberg"
