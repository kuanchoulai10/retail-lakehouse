from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from configs.jobs_repo_backend import JobsRepoBackend
from configs.k8s_settings import K8sSettings
from configs.postgres_settings import PostgresSettings
from configs.sqlite_settings import SqliteSettings


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BACKEND_",
        env_nested_delimiter="__",
    )

    jobs_repo_backend: JobsRepoBackend = JobsRepoBackend.IN_MEMORY
    k8s: K8sSettings = Field(default_factory=K8sSettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    sqlite: SqliteSettings = Field(default_factory=SqliteSettings)
