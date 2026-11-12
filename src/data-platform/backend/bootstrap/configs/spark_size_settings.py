"""Define the SparkSizeSettings configuration model."""

from __future__ import annotations

from pydantic import BaseModel


class SparkSizeSettings(BaseModel):
    """Memory and executor count of one Spark size; cores stay at the Spark settings' values."""

    driver_memory: str
    executor_memory: str
    executor_instances: int = 1
