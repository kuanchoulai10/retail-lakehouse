"""Provide top-level settings for Iceberg table maintenance jobs."""

from pydantic_settings import BaseSettings, SettingsConfigDict

from .base import JobType
from .jobs import ExpireSnapshotsConfig, RemoveOrphanFilesConfig, RewriteDataFilesConfig, RewriteManifestsConfig


class JobSettings(BaseSettings):
    """Top-level settings for Iceberg table maintenance jobs.

    Env vars (prefix: GLAC_):
      GLAC_JOB_TYPE    required  expire_snapshots | remove_orphan_files | rewrite_data_files | rewrite_manifests
      GLAC_CATALOG     optional  Iceberg catalog name registered in Spark, default spark_catalog

    Job-specific config is passed via nested env vars using __ as delimiter, e.g.:
      GLAC_EXPIRE_SNAPSHOTS__TABLE=inventory.orders
      GLAC_REWRITE_DATA_FILES__TABLE=inventory.orders
      GLAC_REWRITE_DATA_FILES__STRATEGY=sort
    """

    model_config = SettingsConfigDict(
        env_prefix="GLAC_",
        env_nested_delimiter="__",
        nested_model_default_partial_update=True,
        cli_parse_args=True,
    )

    job_type: JobType
    catalog: str = "spark_catalog"

    expire_snapshots: ExpireSnapshotsConfig = ExpireSnapshotsConfig()
    remove_orphan_files: RemoveOrphanFilesConfig = RemoveOrphanFilesConfig()
    rewrite_data_files: RewriteDataFilesConfig = RewriteDataFilesConfig()
    rewrite_manifests: RewriteManifestsConfig = RewriteManifestsConfig()
