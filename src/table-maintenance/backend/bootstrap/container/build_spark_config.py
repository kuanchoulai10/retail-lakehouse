"""Provide the build_spark_config function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from adapter.outbound.table_maintenance_run.k8s.spark_k8s_config import SparkK8sConfig

if TYPE_CHECKING:
    from bootstrap.configs.app_settings import AppSettings


def build_spark_config(settings: AppSettings) -> SparkK8sConfig:
    """Combine the Spark and catalog settings into the SparkApplication config."""
    spark = settings.spark
    catalog = settings.catalog
    return SparkK8sConfig(
        image=spark.image,
        service_account=spark.service_account,
        catalog_uri=catalog.uri,
        catalog_credential_secret=spark.catalog_credential_secret,
        s3_endpoint=catalog.s3_endpoint,
        s3_secret_name=spark.s3_secret_name,
        namespace=spark.namespace,
        image_pull_policy=spark.image_pull_policy,
        spark_version=spark.spark_version,
        iceberg_version=spark.iceberg_version,
        catalog_scope=catalog.scope,
        s3_path_style_access=catalog.s3_path_style_access,
        s3_region=catalog.s3_region,
        main_application_file=spark.main_application_file,
        driver_cores=spark.driver_cores,
        driver_memory=spark.driver_memory,
        executor_instances=spark.executor_instances,
        executor_cores=spark.executor_cores,
        executor_memory=spark.executor_memory,
    )
