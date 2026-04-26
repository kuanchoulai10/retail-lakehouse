"""Define the K8sExecutorConfig for system-level Spark settings."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class K8sExecutorConfig:
    """System-level configuration for the K8s executor adapter.

    These values are the same for all jobs and are injected by bootstrap
    from AppSettings.k8s at composition time.
    """

    namespace: str
    image: str
    image_pull_policy: str
    spark_version: str
    service_account: str
    iceberg_jar: str
    iceberg_aws_jar: str
