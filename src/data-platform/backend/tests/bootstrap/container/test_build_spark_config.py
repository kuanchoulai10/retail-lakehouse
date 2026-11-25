"""Test the Spark runtime configuration built from the application settings."""

from __future__ import annotations

from bootstrap.configs import CatalogSettings, SparkSettings, SparkSizeSettings, SparkVolcanoSettings, WorkerSettings
from bootstrap.container import build_spark_config
from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s import (
    SparkK8sConfig,
    SparkSizeResources,
    VolcanoSettings,
)


def test_spark_config_combines_spark_and_catalog_settings():
    """The Spark config combines the Spark and catalog settings."""
    settings = WorkerSettings(
        catalog=CatalogSettings(
            uri="http://polaris:8181/api/catalog",
            scope="PRINCIPAL_ROLE:X",
            s3_endpoint="http://rustfs:9000",
            s3_path_style_access=False,
            s3_region="eu-1",
        ),
        spark=SparkSettings(
            image="spark:1",
            image_pull_policy="IfNotPresent",
            service_account="sa",
            catalog_credential_secret="polaris-cred",
            s3_secret_name="s3-cred",
            namespace="ops",
            spark_version="4.0.1",
            iceberg_version="1.10.2",
            hadoop_version="3.4.2",
            aws_sdk_version="2.34.0",
            event_log_dir="s3a://other-logs/",
            main_application_file="local:///main.py",
            driver_cores=2,
            driver_core_limit="2500m",
            executor_cores=4,
            executor_core_limit="5",
            size_s=SparkSizeSettings(driver_memory="512m", executor_memory="640m"),
            size_m=SparkSizeSettings(driver_memory="2g", executor_memory="4g", executor_instances=3),
            size_l=SparkSizeSettings(driver_memory="3g", executor_memory="6g", executor_instances=2),
        ),
    )

    assert build_spark_config(settings.spark, settings.catalog) == SparkK8sConfig(
        image="spark:1",
        service_account="sa",
        catalog_uri="http://polaris:8181/api/catalog",
        catalog_credential_secret="polaris-cred",
        s3_endpoint="http://rustfs:9000",
        s3_secret_name="s3-cred",
        namespace="ops",
        image_pull_policy="IfNotPresent",
        spark_version="4.0.1",
        iceberg_version="1.10.2",
        hadoop_version="3.4.2",
        aws_sdk_version="2.34.0",
        event_log_dir="s3a://other-logs/",
        catalog_scope="PRINCIPAL_ROLE:X",
        s3_path_style_access=False,
        s3_region="eu-1",
        main_application_file="local:///main.py",
        driver_cores=2,
        driver_core_limit="2500m",
        executor_cores=4,
        executor_core_limit="5",
        sizes={
            "S": SparkSizeResources(driver_memory="512m", executor_memory="640m", executor_instances=1),
            "M": SparkSizeResources(driver_memory="2g", executor_memory="4g", executor_instances=3),
            "L": SparkSizeResources(driver_memory="3g", executor_memory="6g", executor_instances=2),
        },
    )


def test_default_spark_settings_match_the_runtime_defaults():
    """The default Spark settings give the expected namespace, Spark and Iceberg versions."""
    config = build_spark_config(SparkSettings(), CatalogSettings())

    assert config.namespace == "lakehouse-maintenance-operations"
    assert config.spark_version == "4.0.0"
    assert config.iceberg_version == "1.10.1"
    assert config.hadoop_version == "3.4.1"
    assert config.aws_sdk_version == "2.33.0"
    assert config.event_log_dir == "s3a://spark-event-logs/"
    assert config.image_pull_policy == "Never"


def test_default_sizes_reach_the_spark_config():
    """With no settings the config holds the default S, M and L memory."""
    assert build_spark_config(SparkSettings(), CatalogSettings()).sizes == {
        "S": SparkSizeResources(driver_memory="768m", executor_memory="768m", executor_instances=1),
        "M": SparkSizeResources(driver_memory="1g", executor_memory="1536m", executor_instances=1),
        "L": SparkSizeResources(driver_memory="1536m", executor_memory="2g", executor_instances=1),
    }


def test_volcano_settings_reach_the_spark_config():
    """The Volcano queue names and class prefix come through to the config."""
    volcano = SparkVolcanoSettings(queue="q", urgent_queue="uq", priority_class_prefix="pc")

    config = build_spark_config(SparkSettings(volcano=volcano), CatalogSettings())

    assert config.volcano == VolcanoSettings(queue="q", urgent_queue="uq", priority_class_prefix="pc")


def test_default_volcano_settings_reach_the_spark_config():
    """With no settings the config holds the default queues and prefix."""
    assert build_spark_config(SparkSettings(), CatalogSettings()).volcano == VolcanoSettings()
