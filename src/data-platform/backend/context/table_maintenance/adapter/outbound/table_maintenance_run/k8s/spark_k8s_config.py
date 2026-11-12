"""Define the SparkK8sConfig."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.spark_size_resources import (
    SparkSizeResources,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

DEFAULT_SIZES: Mapping[str, SparkSizeResources] = MappingProxyType(
    {
        "S": SparkSizeResources(driver_memory="768m", executor_memory="768m"),
        "M": SparkSizeResources(driver_memory="1g", executor_memory="1536m"),
        "L": SparkSizeResources(driver_memory="1536m", executor_memory="2g"),
    }
)


@dataclass(frozen=True)
class SparkK8sConfig:
    """Hold the settings to render a maintenance SparkApplication.

    ``sizes`` maps each size name to the memory and executor count a job of that size gets.
    """

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
    driver_core_limit: str = "1"
    executor_cores: int = 1
    executor_core_limit: str = "1"
    sizes: Mapping[str, SparkSizeResources] = field(default_factory=lambda: DEFAULT_SIZES)
