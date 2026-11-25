"""Define the SparkSettings configuration model."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from bootstrap.configs.settings_block import SettingsBlock
from bootstrap.configs.spark_size_settings import SparkSizeSettings
from bootstrap.configs.spark_volcano_settings import SparkVolcanoSettings

SIZE_DEFAULTS: dict[str, dict[str, Any]] = {
    "size_s": {"driver_memory": "768m", "executor_memory": "768m", "executor_instances": 1},
    "size_m": {"driver_memory": "1g", "executor_memory": "1536m", "executor_instances": 1},
    "size_l": {"driver_memory": "1536m", "executor_memory": "2g", "executor_instances": 1},
}


class SparkSettings(SettingsBlock):
    """Settings of the maintenance SparkApplications.

    The catalog URI, scope and S3 endpoint come from the catalog settings. The two
    Secrets live in ``namespace``: ``catalog_credential_secret`` holds the key
    ``credential``; ``s3_secret_name`` holds ``AWS_ACCESS_KEY_ID`` and
    ``AWS_SECRET_ACCESS_KEY``. Each maintenance attempt runs at one of the sizes
    ``size_s``, ``size_m`` or ``size_l``, which set its memory and executor count; a
    size given only in part (one environment variable) keeps its defaults for the rest.
    ``volcano`` names the queues and priority classes the applications are scheduled in.
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
    driver_core_limit: str = "1"
    executor_cores: int = 1
    executor_core_limit: str = "1"
    size_s: SparkSizeSettings = Field(default_factory=lambda: SparkSizeSettings(**SIZE_DEFAULTS["size_s"]))
    size_m: SparkSizeSettings = Field(default_factory=lambda: SparkSizeSettings(**SIZE_DEFAULTS["size_m"]))
    size_l: SparkSizeSettings = Field(default_factory=lambda: SparkSizeSettings(**SIZE_DEFAULTS["size_l"]))
    volcano: SparkVolcanoSettings = Field(default_factory=SparkVolcanoSettings)

    @model_validator(mode="before")
    @classmethod
    def _fill_size_defaults(cls, data: Any) -> Any:
        """Complete a size given only in part with that size's defaults."""
        if not isinstance(data, dict):
            return data
        filled = dict(data)
        for key, defaults in SIZE_DEFAULTS.items():
            given = filled.get(key)
            if isinstance(given, dict):
                filled[key] = {**defaults, **given}
        return filled
