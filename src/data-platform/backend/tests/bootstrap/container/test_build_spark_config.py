from __future__ import annotations

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s import (
    SparkK8sConfig,
)
from bootstrap.configs import AppSettings, CatalogSettings, SparkSettings
from bootstrap.container import build_spark_config


def test_spark_config_combines_spark_and_catalog_settings():
    settings = AppSettings(
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
            driver_memory="2g",
            executor_instances=3,
            executor_cores=4,
            executor_memory="4g",
        ),
    )

    assert build_spark_config(settings) == SparkK8sConfig(
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
        driver_memory="2g",
        executor_instances=3,
        executor_cores=4,
        executor_memory="4g",
    )


def test_default_spark_settings_match_the_runtime_defaults():
    config = build_spark_config(AppSettings())

    assert config.namespace == "lakehouse-maintenance-operations"
    assert config.spark_version == "4.0.0"
    assert config.iceberg_version == "1.10.1"
    assert config.hadoop_version == "3.4.1"
    assert config.aws_sdk_version == "2.33.0"
    assert config.event_log_dir == "s3a://spark-event-logs/"
    assert config.image_pull_policy == "Never"
