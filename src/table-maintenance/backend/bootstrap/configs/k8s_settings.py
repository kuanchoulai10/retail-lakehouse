"""Define the K8sSettings configuration model."""

from __future__ import annotations

from pydantic import BaseModel


class K8sSettings(BaseModel):
    """System-level Kubernetes and Spark configuration.

    Per-job resource settings (driver_memory, executor_memory, executor_instances)
    are modeled on the Job entity via ResourceConfig.
    """

    namespace: str = "default"
    image: str = "localhost:5000/table-maintenance-jobs:latest"
    image_pull_policy: str = "Never"
    spark_version: str = "4.0.0"
    service_account: str = "spark-operator-spark"
    iceberg_jar: str = (
        "https://repo1.maven.org/maven2/org/apache/iceberg/"
        "iceberg-spark-runtime-4.0_2.13/1.10.1/"
        "iceberg-spark-runtime-4.0_2.13-1.10.1.jar"
    )
    iceberg_aws_jar: str = "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/1.10.1/iceberg-aws-bundle-1.10.1.jar"
