"""Define the SparkSettings configuration model."""

from __future__ import annotations

from pydantic import BaseModel


class SparkSettings(BaseModel):
    """Settings of the maintenance SparkApplications.

    The catalog URI, scope and S3 endpoint come from the catalog settings. The two
    Secrets live in ``namespace``: ``catalog_credential_secret`` holds the key
    ``credential``; ``s3_secret_name`` holds ``AWS_ACCESS_KEY_ID`` and
    ``AWS_SECRET_ACCESS_KEY``.
    """

    image: str = "table-maintenance-spark:0.1.0"
    image_pull_policy: str = "Never"
    service_account: str = "table-maintenance-spark"
    catalog_credential_secret: str = "table-maintenance-polaris-credential"
    s3_secret_name: str = "table-maintenance-s3-credentials"
    namespace: str = "lakehouse-maintenance-operations"
    spark_version: str = "4.0.0"
    iceberg_version: str = "1.10.1"
    hadoop_version: str = "3.4.1"
    aws_sdk_version: str = "2.33.0"
    event_log_dir: str = "s3a://spark-event-logs/"
    main_application_file: str = "local:///opt/spark/work-dir/main.py"
    driver_cores: int = 1
    driver_memory: str = "1g"
    executor_instances: int = 1
    executor_cores: int = 1
    executor_memory: str = "1g"
