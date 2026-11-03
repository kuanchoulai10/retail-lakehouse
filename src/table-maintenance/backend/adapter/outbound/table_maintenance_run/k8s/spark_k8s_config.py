"""Define the SparkK8sConfig."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SparkK8sConfig:
    """Hold the settings to render a maintenance SparkApplication."""

    image: str
    service_account: str
    catalog_uri: str
    catalog_credential_secret: str
    s3_endpoint: str
    s3_secret_name: str
    namespace: str = "lakehouse-maintenance-operations"
    image_pull_policy: str = "Never"
    spark_version: str = "4.0.0"
    iceberg_version: str = "1.10.1"
    hadoop_version: str = "3.4.1"
    aws_sdk_version: str = "2.33.0"
    event_log_dir: str = "s3a://spark-event-logs/"
    catalog_scope: str = "PRINCIPAL_ROLE:ALL"
    s3_path_style_access: bool = True
    s3_region: str = "dummy-region"
    main_application_file: str = "local:///opt/spark/work-dir/main.py"
    driver_cores: int = 1
    driver_memory: str = "1g"
    executor_instances: int = 1
    executor_cores: int = 1
    executor_memory: str = "1g"
