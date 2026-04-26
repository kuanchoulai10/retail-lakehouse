"""Define the ResourceConfig value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class ResourceConfig(ValueObject):
    """Per-job Spark resource configuration.

    Provides sensible defaults so that jobs can be created without
    specifying resource requirements explicitly.
    """

    driver_memory: str = "512m"
    executor_memory: str = "1g"
    executor_instances: int = 1
